import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from "recharts";

const nodeData = [
  { name: "Allocated", value: 18, color: "hsl(var(--primary))" },
  { name: "Idle", value: 14, color: "hsl(var(--muted))" },
];

const partitionData = [
  { partition: "GPU", allocated: 8, idle: 4 },
  { partition: "CPU", allocated: 6, idle: 6 },
  { partition: "Memory", allocated: 4, idle: 4 },
];

const memoryData = [
  { name: "Used", value: 2048, color: "hsl(var(--chart-2))" },
  { name: "Free", value: 1024, color: "hsl(var(--muted))" },
];

const ResourceMonitor = () => {
  const totalNodes = nodeData.reduce((sum, item) => sum + item.value, 0);
  const utilizationPercent = ((nodeData[0].value / totalNodes) * 100).toFixed(1);

  const totalMemory = memoryData.reduce((sum, item) => sum + item.value, 0);
  const memoryUsedPercent = ((memoryData[0].value / totalMemory) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Nodes</CardDescription>
            <CardTitle className="text-3xl">{totalNodes}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {nodeData[0].value} allocated • {nodeData[1].value} idle
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Utilization</CardDescription>
            <CardTitle className="text-3xl">{utilizationPercent}%</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Cluster efficiency rate
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
              {memoryData[0].value} GB / {totalMemory} GB
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

        {/* Partition Usage Bar Chart */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Per Partition Node Usage</CardTitle>
            <CardDescription>Resource allocation across partitions</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={partitionData}>
                <XAxis dataKey="partition" stroke="hsl(var(--muted-foreground))" />
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
                <Legend wrapperStyle={{ color: 'hsl(var(--foreground))' }} />
                <Bar dataKey="allocated" fill="hsl(var(--primary))" name="Allocated" />
                <Bar dataKey="idle" fill="hsl(var(--muted))" name="Idle" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ResourceMonitor;
