import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MembersPanel from './MembersPanel';

const LATTICE: Record<string, object> = {
  alpha: { project_id: 'alpha', work_id: 'gospels', parent: 'dr-full', children: [], siblings: ['beta'], collections: ['c1'] },
  beta: { project_id: 'beta', work_id: 'gospels', parent: null, children: [], siblings: ['alpha'], collections: ['c1'] },
};

function stubFetch(putSpy?: (url: string, init?: RequestInit) => void) {
  return vi.fn((url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') {
      putSpy?.(url, init);
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ id: 'c1' }) });
    }
    const m = url.match(/\/api\/projects\/(\w+)\/lattice/);
    return Promise.resolve({ ok: true, json: () => Promise.resolve(m ? LATTICE[m[1]] : {}) });
  });
}

describe('MembersPanel', () => {
  beforeEach(() => vi.stubGlobal('fetch', stubFetch()));
  afterEach(() => vi.unstubAllGlobals());

  it('renders members with their lattice lineage', async () => {
    render(<MembersPanel collectionId="c1" members={['alpha', 'beta']} roles={{}} onMember={() => {}} />);
    expect(screen.getByText('alpha')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/from/)).toBeInTheDocument());  // alpha's parent lineage
    expect(screen.getAllByText('gospels').length).toBe(2);  // work_id per member
  });

  it('a member opens its single-text browser', () => {
    const onMember = vi.fn();
    render(<MembersPanel collectionId="c1" members={['alpha']} roles={{}} onMember={onMember} />);
    fireEvent.click(screen.getByText('alpha'));
    expect(onMember).toHaveBeenCalledWith('alpha');
  });

  it('toggling a member to root PUTs the role (root re-coordination)', async () => {
    const put = vi.fn();
    const onRolesChanged = vi.fn();
    vi.stubGlobal('fetch', stubFetch(put));
    render(<MembersPanel collectionId="c1" members={['alpha']} roles={{}} onMember={() => {}} onRolesChanged={onRolesChanged} />);

    fireEvent.click(screen.getByText('member'));  // current role button
    await waitFor(() => expect(put).toHaveBeenCalled());
    const [url, init] = put.mock.calls[0];
    expect(url).toBe('/api/collections/c1/roles/alpha');
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({ role: 'root' });
    expect(onRolesChanged).toHaveBeenCalled();
  });

  it('shows an existing root role', () => {
    render(<MembersPanel collectionId="c1" members={['alpha']} roles={{ alpha: 'root' }} onMember={() => {}} />);
    const btn = screen.getByRole('button', { name: 'root' });
    expect(btn).toHaveAttribute('aria-pressed', 'true');
  });
});
