import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { PlayCircle, Clock } from "lucide-react";

const queueOverview = [
  { status: "Running", count: 12, color: "hsl(var(--primary))" },
  { status: "Pending", count: 8, color: "hsl(var(--warning))" },
];

const partitionJobs = [
  { partition: "GPU", running: 6, pending: 3 },
  { partition: "CPU", running: 4, pending: 3 },
  { partition: "Memory", running: 2, pending: 2 },
];

const JobQueue = () => {
  const totalJobs = queueOverview.reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Jobs in Queue</CardDescription>
            <CardTitle className="text-3xl">{totalJobs}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Active and pending jobs
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription className="flex items-center gap-2">
              <PlayCircle className="h-4 w-4 text-primary" />
              Running Jobs
            </CardDescription>
            <CardTitle className="text-3xl text-primary">
              {queueOverview[0].count}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Currently executing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-warning" />
              Pending Jobs
            </CardDescription>
            <CardTitle className="text-3xl text-warning">
              {queueOverview[1].count}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Waiting in queue
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Queue Status Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Job Queue by Partition</CardTitle>
          <CardDescription>Running and pending jobs across partitions</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={partitionJobs}>
              <XAxis 
                dataKey="partition" 
                stroke="hsl(var(--muted-foreground))"
              />
              <YAxis stroke="hsl(var(--muted-foreground))" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  color: 'hsl(var(--foreground))'
                }}
                cursor={{ fill: 'hsl(var(--muted))' }}
              />
              <Bar dataKey="running" fill="hsl(var(--primary))" name="Running" />
              <Bar dataKey="pending" fill="hsl(var(--warning))" name="Pending" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Job Details List */}
      <Card>
        <CardHeader>
          <CardTitle>Queue Details</CardTitle>
          <CardDescription>Jobs currently in the queue</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { id: "12345", name: "Deep Learning Model", partition: "GPU", status: "running", priority: "High" },
              { id: "12346", name: "Data Processing", partition: "CPU", status: "running", priority: "Medium" },
              { id: "12347", name: "Simulation Task", partition: "GPU", status: "pending", priority: "High" },
              { id: "12348", name: "Analysis Job", partition: "Memory", status: "pending", priority: "Low" },
            ].map((job) => (
              <div
                key={job.id}
                className="flex items-center justify-between p-3 rounded-lg border border-border bg-card hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  {job.status === "running" ? (
                    <PlayCircle className="h-4 w-4 text-primary" />
                  ) : (
                    <Clock className="h-4 w-4 text-warning" />
                  )}
                  <div>
                    <p className="font-medium">{job.name}</p>
                    <p className="text-sm text-muted-foreground">
                      Job ID: {job.id} • {job.partition}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className={
                    job.priority === "High" 
                      ? "border-destructive/40 text-destructive"
                      : job.priority === "Medium"
                      ? "border-warning/40 text-warning"
                      : "border-muted-foreground/40"
                  }>
                    {job.priority}
                  </Badge>
                  <Badge variant="outline" className={
                    job.status === "running"
                      ? "bg-primary/10 text-primary border-primary/20"
                      : "bg-warning/10 text-warning border-warning/20"
                  }>
                    {job.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default JobQueue;
