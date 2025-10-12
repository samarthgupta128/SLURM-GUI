import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import JobHistory from "@/components/dashboard/JobHistory";
import SubmitJob from "@/components/dashboard/SubmitJob";
import ResourceMonitor from "@/components/dashboard/ResourceMonitor";
import PartitionStatus from "@/components/dashboard/PartitionStatus";
import JobQueue from "@/components/dashboard/JobQueue";
import { LayoutDashboard, Plus, Activity, Layers, List } from "lucide-react";

const Dashboard = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const username = localStorage.getItem("username");
    if (!username) {
      navigate("/");
    }
  }, [navigate]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Manage your HPC workloads and monitor cluster resources
          </p>
        </div>

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="bg-muted">
            <TabsTrigger value="overview" className="gap-2">
              <LayoutDashboard className="h-4 w-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="submit" className="gap-2">
              <Plus className="h-4 w-4" />
              Submit Job
            </TabsTrigger>
            <TabsTrigger value="resources" className="gap-2">
              <Activity className="h-4 w-4" />
              Resources
            </TabsTrigger>
            <TabsTrigger value="partitions" className="gap-2">
              <Layers className="h-4 w-4" />
              Partitions
            </TabsTrigger>
            <TabsTrigger value="queue" className="gap-2">
              <List className="h-4 w-4" />
              Job Queue
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <JobHistory />
          </TabsContent>

          <TabsContent value="submit">
            <SubmitJob />
          </TabsContent>

          <TabsContent value="resources">
            <ResourceMonitor />
          </TabsContent>

          <TabsContent value="partitions">
            <PartitionStatus />
          </TabsContent>

          <TabsContent value="queue">
            <JobQueue />
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
