import * as RadixTooltip from '@radix-ui/react-tooltip';
import type { ReactNode } from 'react';

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
  align?: 'start' | 'center' | 'end';
  delayDuration?: number;
}

export function Tooltip({
  content,
  children,
  side = 'top',
  align = 'center',
  delayDuration = 300,
}: TooltipProps) {
  if (!content) return <>{children}</>;

  return (
    <RadixTooltip.Root delayDuration={delayDuration}>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side={side}
          align={align}
          sideOffset={5}
          className="z-[var(--z-tooltip)] max-w-72 rounded-[var(--radius-md)] bg-[#1a1a1a] px-3 py-1.5 text-xs leading-snug text-white shadow-[var(--shadow-tooltip)] animate-[tooltip-fade-in_var(--duration-fast)_ease-out] data-[state=closed]:animate-[tooltip-fade-out_var(--duration-fast)_ease-in]"
        >
          {content}
          <RadixTooltip.Arrow className="fill-[#1a1a1a]" />
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}

export function TooltipProvider({ children }: { children: ReactNode }) {
  return (
    <RadixTooltip.Provider delayDuration={300} skipDelayDuration={100}>
      {children}
    </RadixTooltip.Provider>
  );
}
