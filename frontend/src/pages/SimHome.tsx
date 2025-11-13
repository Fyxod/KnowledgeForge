import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import SimNavbar from '@/components/SimNavbar';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const SectionCard: React.FC<{
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  description: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}> = ({ icon, title, subtitle, description, onClick, disabled }) => {
  const baseClasses =
    "group w-full sm:w-[260px] h-auto sm:h-[400px] rounded-xl border-2 bg-muted dark:bg-card shadow-sm transition-all duration-300 flex flex-col items-center justify-center text-center gap-4 p-6";

  const enabledHover =
    "hover:shadow-xl hover:bg-primary/10 dark:hover:shadow-2xl dark:hover:bg-primary/20";

  const disabledClasses = "opacity-60 cursor-not-allowed hover:shadow-none hover:bg-muted dark:hover:bg-card";

  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={`${baseClasses} ${disabled ? disabledClasses : enabledHover}`}
      style={{ borderColor: disabled ? 'hsl(var(--border))' : 'hsl(var(--primary))' }}
    >
      <div className={`w-24 h-24 grid place-items-center ${disabled ? 'text-muted-foreground opacity-40 filter grayscale dark:text-muted-foreground' : 'text-primary'}`}>
        {icon}
      </div>
      <div>
        <h3 className={`text-lg font-semibold ${disabled ? 'text-muted-foreground' : 'text-foreground'}`}>{title}</h3>
        <p className={`text-sm mt-1 ${disabled ? 'text-muted-foreground' : 'text-muted-foreground/80'}`}>{subtitle}</p>
        <p className={`text-xs mt-2 leading-relaxed ${disabled ? 'text-muted-foreground' : 'text-muted-foreground/80 dark:text-muted-foreground'}`}>{description}</p>
      </div>
    </button>
  );
};

const SimHome: React.FC = () => {
  const navigate = useNavigate();

  const goto = (path?: string) => {
    if (!path) {
      toast.info('Target page not wired yet');
      return;
    }
    navigate(path);
  };

  return (
    <div className="min-h-screen bg-muted/40 dark:bg-background text-foreground flex flex-col">
      <SimNavbar />
      <main className="mx-auto max-w-7xl px-6 w-full flex-1 overflow-auto">
        <section className="py-12 md:py-16">
          <div className="flex items-center justify-center gap-8">
            <img src="/hero-decor.svg" alt="decor" className="w-28 h-28 md:w-32 md:h-32 object-contain select-none" draggable="false" />
            <div className="text-center">
              <h2 className="text-5xl md:text-6xl font-bold tracking-tight">Welcome to SIM</h2>
              <p className="text-2xl md:text-3xl mt-3 text-foreground/80 dark:text-foreground">Your one-stop portal to SRI-B Strategy</p>
            </div>
          </div>

          {/* Four Cards */}
          <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 justify-center">
            <SectionCard
              icon={<img src="/tile-intelligent-augmenter.svg" alt="Intelligent Augmenter" className="w-15 h-15 select-none" draggable="false" />}
              title="Intelligent Knowledge Augmenter"
              subtitle=""
              description={(
                <>
                  <span className="italic text-foreground/90 dark:text-foreground">Knowledge Graph Q&A
                  <br />&<br />
                  External Context Engine</span>
                </>
              )}
              onClick={() => goto("/dashboard")}
            />
            <SectionCard
              icon={<img src="/tile-program-orchestrator.svg" alt="Program Orchestrator" className="w-15 h-15 select-none" draggable="false" />}
              title="Automatic Program Orchestrator"
              subtitle=""
              // description={"Strategic Coordination &\nExecution Management\nSystem"}
              description={(
                <>
                  <span className="italic text-foreground/90 dark:text-foreground">Strategic Coordination
                  <br />&<br />
                  Execution Management System</span>
                </>
              )}

              onClick={() => goto()}
              disabled
            />
            <SectionCard
              icon={<img src="/tile-cognitive-foresight.svg" alt="Cognitive Foresight" className="w-15 h-15 select-none" draggable="false" />}
              title="Cognitive Foresight Engine"
              subtitle=""
              // description={"Strategic Futures\nExploration &\nTechnology Forecasting\nSystem"}
              description={(
                <>
                  <span className="italic text-foreground/90 dark:text-foreground">Strategic Futures\nExploration 
                  <br />&<br />
                  Technology Forecasting System</span>
                </>
              )}

              onClick={() => goto()}
              disabled
            />
            <SectionCard
              icon={<img src="/tile-rd-insights.svg" alt="R&D Insights" className="w-15 h-15 select-none" draggable="false" />}
              title="R&D Insights Analyzer"
              subtitle=""
              // description={"Pattern Recognition &\nAnalytical Intelligence\nEngine"}
              description={(
                <>
                  <span className="italic text-foreground/90 dark:text-foreground">Pattern Recognition
                  <br />&<br />
                  Analytical Intelligence Engine</span>
                </>
              )}

              onClick={() => goto()}
              disabled
            />
          </div>

          {/* Powered by KG */}
          <div className="mt-12 flex flex-col md:flex-row items-center gap-4 md:gap-6">
            {/* Left: Logo + stacked text */}
            <div className="flex items-center gap-4">
              <img src="/sim-logo.svg" alt="SIM Logo" className="w-20 h-20 select-none" draggable="false" />
              <div className="leading-tight">
                <p className="text-base text-muted-foreground">Powered by</p>
                <p className="mt-1 text-3xl md:text-4xl font-semibold tracking-tight">R&D Knowledge Graph</p>
              </div>
            </div>

            {/* Right: CTA buttons */}
            <div className="flex flex-wrap gap-3 md:gap-4 md:ml-6">
              <Button
                variant="outline"
                className="rounded-xl border-2 border-primary bg-muted text-primary hover:bg-primary/10 dark:bg-card dark:text-primary dark:hover:bg-primary/20"
                onClick={() => goto()}
              >
                See all Document Clusters <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
              <Button
                variant="outline"
                className="rounded-xl border-2 border-primary bg-muted text-primary hover:bg-primary/10 dark:bg-card dark:text-primary dark:hover:bg-primary/20"
                onClick={() => goto()}
              >
                See all Knowledge Graphs <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer note */}
      <footer className="py-6 text-center text-sm text-muted-foreground">Powered by PRISM</footer>
    </div>
  );
};

export default SimHome;
