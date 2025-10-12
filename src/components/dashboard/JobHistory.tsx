import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle, Clock, PlayCircle } from "lucide-react";

interface Job {
  id: string;
  name: string;
  status: "completed" | "failed" | "running" | "pending";
  nodes: number;
  time: string;
  submitted: string;
}

const mockJobs: Job[] = [
  { id: "12345", name: "Neural Network Training", status: "completed", nodes: 4, time: "2h 34m", submitted: "2 hours ago" },
  { id: "12344", name: "Molecular Dynamics", status: "running", nodes: 8, time: "1h 12m", submitted: "1 hour ago" },
  { id: "12343", name: "Data Analysis", status: "completed", nodes: 2, time: "45m", submitted: "5 hours ago" },
  { id: "12342", name: "Simulation Run", status: "failed", nodes: 4, time: "12m", submitted: "6 hours ago" },
  { id: "12341", name: "Batch Processing", status: "pending", nodes: 3, time: "-", submitted: "30 min ago" },
];

const JobHistory = () => {
  const getStatusIcon = (status: Job["status"]) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-destructive" />;
      case "running":
        return <PlayCircle className="h-4 w-4 text-primary" />;
      case "pending":
        return <Clock className="h-4 w-4 text-warning" />;
    }
  };

  const getStatusColor = (status: Job["status"]) => {
    switch (status) {
      case "completed":
        return "bg-success/10 text-success border-success/20";
      case "failed":
        return "bg-destructive/10 text-destructive border-destructive/20";
      case "running":
        return "bg-primary/10 text-primary border-primary/20";
      case "pending":
        return "bg-warning/10 text-warning border-warning/20";
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Jobs</CardTitle>
        <CardDescription>Latest job submissions and their status</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {mockJobs.map((job) => (
            <div
              key={job.id}
              className="flex items-center justify-between p-4 rounded-lg border border-border bg-card hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start gap-4 flex-1">
                <div className="mt-1">{getStatusIcon(job.status)}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-medium">{job.name}</h4>
                    <Badge variant="outline" className={getStatusColor(job.status)}>
                      {job.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>Job ID: {job.id}</span>
                    <span>•</span>
                    <span>{job.nodes} nodes</span>
                    <span>•</span>
                    <span>Runtime: {job.time}</span>
                  </div>
                </div>
              </div>
              <div className="text-sm text-muted-foreground">{job.submitted}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default JobHistory;
