import { Link, NavLink, Outlet } from "react-router-dom";
import { Briefcase, Settings, Upload } from "lucide-react";

export function Layout() {
  const link = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border bg-card/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="font-semibold text-lg flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-primary" />
            Vacature Explorer
          </Link>
          <nav className="flex gap-1">
            <NavLink to="/" className={link} end>
              Vacatures
            </NavLink>
            <NavLink to="/match" className={link}>
              <span className="flex items-center gap-1"><Upload className="h-4 w-4" /> CV-match</span>
            </NavLink>
            <NavLink to="/beheer" className={link}>
              <span className="flex items-center gap-1"><Settings className="h-4 w-4" /> Beheer</span>
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
