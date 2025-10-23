import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { PlayCircle, Clock } from "lucide-react";

type QueueJob = {
  job_id: string;
  user: string;
  name: string;
  state: string;
  time: string;
  nodes: string;
  reason: string;
};

const JobQueue = () => {
  const [jobs, setJobs] = useState<QueueJob[]>([]);
  const [partitionsSummary, setPartitionsSummary] = useState<{ partition: string; running: number; pending: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      setLoading(true);
      try {
        const qRes = await fetch("/api/queue");
        const qJson = qRes.ok ? await qRes.json() : { jobs: [] };
        const rawJobs: QueueJob[] = Array.isArray(qJson.jobs) ? qJson.jobs : [];

        // Try to get partition breakdown from /api/resources or debug sample
        let resourcesJson: any = null;
        try {
          const r = await fetch("/api/resources");
          if (r.ok) resourcesJson = await r.json();
        } catch (e) {
          // ignore
        }
        if (!resourcesJson) {
          try {
            const r2 = await fetch("/api/debug/sample-resources");
            if (r2.ok) resourcesJson = await r2.json();
          } catch (e) {
            // ignore
          }
        }

        // Build partition summary from jobs (best-effort parsing if resources not available)
        const partitionMap: Record<string, { running: number; pending: number }> = {};
        rawJobs.forEach((j) => {
          // State mapping: R -> running, PD -> pending, others grouped
          const state = (j.state || "").toUpperCase();
          const isRunning = state.startsWith("R") || state.includes("RUN");
          const isPending = state.startsWith("P") || state.includes("PEND");

          // Try to extract partition from reason or nodes fields (best-effort)
          const partition = (j.reason && j.reason.split(" ")[0]) || (j.nodes && j.nodes.split(":")[0]) || "unknown";
          if (!partitionMap[partition]) partitionMap[partition] = { running: 0, pending: 0 };
          if (isRunning) partitionMap[partition].running += 1;
          else if (isPending) partitionMap[partition].pending += 1;
          else partitionMap[partition].pending += 1;
        });

        // If partition data exists in resourcesJson, prefer it (sample-resources format)
        if (resourcesJson && Array.isArray(resourcesJson.partitions)) {
          const preferred: typeof partitionsSummary = resourcesJson.partitions.map((p: any) => ({
            partition: p.name || "unknown",
            running: p.allocated_nodes || 0,
            pending: Math.max(0, (p.total_nodes || 0) - (p.allocated_nodes || 0)),
          }));
          if (mounted) setPartitionsSummary(preferred);
        } else {
          const arr = Object.entries(partitionMap).map(([partition, counts]) => ({ partition, running: counts.running, pending: counts.pending }));
          if (mounted) setPartitionsSummary(arr);
        }

        if (mounted) setJobs(rawJobs);
      } catch (e) {
        console.error("Failed to load queue/resources:", e);
        if (mounted) setError("Failed to load job queue data");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchData();
    const id = setInterval(fetchData, 30000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const runningCount = jobs.filter((j) => (j.state || "").toUpperCase().startsWith("R") || (j.state || "").toUpperCase().includes("RUN")).length;
  const pendingCount = jobs.length - runningCount;

  const queueOverview = [
    { status: "Running", count: runningCount, color: "hsl(var(--primary))" },
    { status: "Pending", count: pendingCount, color: "hsl(var(--warning))" },
  ];

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Jobs in Queue</CardDescription>
            <CardTitle className="text-3xl">{jobs.length}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Active and pending jobs</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription className="flex items-center gap-2">
              <PlayCircle className="h-4 w-4 text-primary" />
              Running Jobs
            </CardDescription>
            <CardTitle className="text-3xl text-primary">{queueOverview[0].count}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Currently executing</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-warning" />
              Pending Jobs
            </CardDescription>
            <CardTitle className="text-3xl text-warning">{queueOverview[1].count}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Waiting for resources</p>
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
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
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
                {partitionsSummary.map((partition) => {
                  const total = partition.running + partition.pending;
                  const utilization = total > 0 ? ((partition.running / total) * 100).toFixed(0) : "0";

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
                          <span className="text-sm text-muted-foreground min-w-[3ch]">{utilization}%</span>
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
