import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from "recharts";
import { useEffect, useState } from "react";
import { Progress } from "@/components/ui/progress";

interface ClusterStats {
  total_nodes: number;
  allocated_nodes: number;
  total_cpus: number;
  allocated_cpus: number;
  total_memory: number;
  allocated_memory: number;
  partitions: Array<{
    name: string;
    total_nodes: number;
    allocated_nodes: number;
    total_cpus: number;
    allocated_cpus: number;
    total_memory: number;
    allocated_memory: number;
  }>;
  nodes: Array<{
    name: string;
    state: string;
    partition: string;
    cpus_allocated: number;
    cpus_idle: number;
    cpus_total: number;
    memory_total: number;
    memory_free: number;
    memory_used: number;
  }>;
  gpu_nodes: Record<string, string>;
}

const ResourceMonitor = () => {
  const [stats, setStats] = useState<ClusterStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/api/resources', {
          headers: {
            'Accept': 'application/json',
          }
        });
        
        const text = await response.text();
        let data;
        try {
          data = JSON.parse(text);
        } catch (parseError) {
          console.error('Failed to parse response:', text);
          throw new Error('Invalid response format from server');
        }

        if (!response.ok) {
          throw new Error(data.error || 'Failed to fetch cluster stats');
        }

        if (data.error) {
          console.warn('Server reported error:', data.error);
        }

        setStats(data);
        setError(null);
      } catch (err) {
        console.error('Resource fetch error:', err);
        setError(err instanceof Error ? err.message : 'Failed to load resources');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Progress value={30} className="w-40" />
          <p className="mt-2 text-sm text-muted-foreground">Loading cluster stats...</p>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="p-4 text-center">
        <p className="text-red-500">{error || 'Failed to load cluster statistics'}</p>
      </div>
    );
  }

  const nodeData = [
    { name: "Allocated", value: stats.allocated_nodes, color: "hsl(var(--primary))" },
    { name: "Idle", value: stats.total_nodes - stats.allocated_nodes, color: "hsl(var(--muted))" },
  ];

  const memoryData = [
    { name: "Used", value: Math.round(stats.allocated_memory), color: "hsl(var(--chart-2))" },
    { name: "Free", value: Math.round(stats.total_memory - stats.allocated_memory), color: "hsl(var(--muted))" },
  ];

  const utilizationPercent = ((stats.allocated_nodes / stats.total_nodes) * 100).toFixed(1);
  const memoryUsedPercent = ((stats.allocated_memory / stats.total_memory) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Nodes</CardDescription>
            <CardTitle className="text-3xl">{stats.total_nodes}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {stats.allocated_nodes} allocated • {stats.total_nodes - stats.allocated_nodes} idle
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>CPU Utilization</CardDescription>
            <CardTitle className="text-3xl">
              {((stats.allocated_cpus / stats.total_cpus) * 100).toFixed(1)}%
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {stats.allocated_cpus} / {stats.total_cpus} CPUs in use
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Memory Usage</CardDescription>
            <CardTitle className="text-3xl">{memoryUsedPercent}%</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {Math.round(stats.allocated_memory)} GB / {Math.round(stats.total_memory)} GB
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Node Allocation Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Node Allocation</CardTitle>
            <CardDescription>Allocated vs Idle nodes</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={nodeData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {nodeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--popover))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    color: 'hsl(var(--foreground))'
                  }}
                  cursor={{ fill: 'hsl(var(--muted))' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Memory Usage Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Memory Distribution</CardTitle>
            <CardDescription>Used vs Free memory (GB)</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={memoryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name} ${value}GB`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {memoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--popover))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    color: 'hsl(var(--foreground))'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Partition Usage */}
        <Card>
          <CardHeader>
            <CardTitle>Partition Usage</CardTitle>
            <CardDescription>Resource allocation by partition</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart
                data={stats.partitions.map(p => ({
                  name: p.name,
                  Allocated: p.allocated_nodes,
                  Idle: p.total_nodes - p.allocated_nodes
                }))}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={100} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--popover))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    color: 'hsl(var(--foreground))'
                  }}
                />
                <Legend />
                <Bar dataKey="Allocated" fill="hsl(var(--primary))" stackId="a" />
                <Bar dataKey="Idle" fill="hsl(var(--muted))" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* GPU Information if available */}
      {Object.keys(stats.gpu_nodes).length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>GPU Nodes</CardTitle>
            <CardDescription>Nodes with GPU resources</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(stats.gpu_nodes).map(([node, gpu]) => (
                <div key={node} className="p-4 border rounded-lg">
                  <p className="font-medium">{node}</p>
                  <p className="text-sm text-muted-foreground">{gpu}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ResourceMonitor;
