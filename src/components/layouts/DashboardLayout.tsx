import { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Server, LogOut, User } from "lucide-react";
import { toast } from "sonner";

interface DashboardLayoutProps {
  children: ReactNode;
}

const DashboardLayout = ({ children }: DashboardLayoutProps) => {
  const navigate = useNavigate();
  const username = localStorage.getItem("username") || "User";
  const userRole = localStorage.getItem("userRole") || "student";

  const handleLogout = () => {
    localStorage.removeItem("username");
    localStorage.removeItem("userRole");
    toast.success("Logged out successfully");
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <Server className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="font-semibold">SLURM Manager</h2>
              <p className="text-xs text-muted-foreground">HPC Workload Control</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted">
              <User className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">{username}</span>
              <span className="text-xs text-muted-foreground capitalize">({userRole})</span>
            </div>
            <Button variant="outline" size="sm" onClick={handleLogout}>
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-6">
        {children}
      </main>
    </div>
  );
};

export default DashboardLayout;
