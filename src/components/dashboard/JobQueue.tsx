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
              Waiting for resources
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Queue Status Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Queue Status Distribution</CardTitle>
          <CardDescription>Running vs pending jobs</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={queueOverview}>
              <XAxis dataKey="status" stroke="hsl(var(--muted-foreground))" />
              <YAxis stroke="hsl(var(--muted-foreground))" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                {queueOverview.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Jobs per Partition Table */}
      <Card>
        <CardHeader>
          <CardTitle>Jobs per Partition</CardTitle>
          <CardDescription>Distribution of jobs across cluster partitions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-medium">Partition</th>
                  <th className="text-left py-3 px-4 font-medium">Running</th>
                  <th className="text-left py-3 px-4 font-medium">Pending</th>
                  <th className="text-left py-3 px-4 font-medium">Total</th>
                  <th className="text-left py-3 px-4 font-medium">Utilization</th>
                </tr>
              </thead>
              <tbody>
                {partitionJobs.map((partition) => {
                  const total = partition.running + partition.pending;
                  const utilization = ((partition.running / total) * 100).toFixed(0);
                  
                  return (
                    <tr key={partition.partition} className="border-b border-border/50 hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{partition.partition} Partition</td>
                      <td className="py-3 px-4">
                        <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
                          {partition.running}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20">
                          {partition.pending}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{total}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-primary rounded-full transition-all"
                              style={{ width: `${utilization}%` }}
                            />
                          </div>
                          <span className="text-sm text-muted-foreground min-w-[3ch]">
                            {utilization}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default JobQueue;
