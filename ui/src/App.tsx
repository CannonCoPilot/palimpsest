import { useEffect } from 'react';
import { useAppStore } from './stores/appStore';
import { useProjectStore } from './stores/projectStore';
import ProjectPicker from './components/ProjectPicker';
import MainLayout from './components/MainLayout';

export default function App() {
  const projectLoaded = useProjectStore((s) => s.loaded);
  const setWorkspace = useAppStore((s) => s.setWorkspace);

  useEffect(() => {
    setWorkspace('/Users/nathanielcannon/Claude/Projects/palimpsest/core/data');
  }, [setWorkspace]);

  return projectLoaded ? <MainLayout /> : <ProjectPicker />;
}
