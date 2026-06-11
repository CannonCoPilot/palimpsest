import AppLayout from './components/Layout/AppLayout';
import { TooltipProvider } from './components/common/Tooltip';

export default function App() {
  return (
    <TooltipProvider>
      <AppLayout />
    </TooltipProvider>
  );
}
