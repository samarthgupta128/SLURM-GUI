import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertCircle, XCircle } from "lucide-react";

interface Partition {
  name: string;
  nodes: number;
  status: "healthy" | "warning" | "error";
}

interface Node {
  id: string;
  partition: string;
  status: "healthy" | "warning" | "error";
  cpu: number;
  memory: number;
}

const partitions: Partition[] = [
  { name: "GPU Partition", nodes: 12, status: "healthy" },
  { name: "CPU Partition", nodes: 12, status: "healthy" },
  { name: "Memory Partition", nodes: 8, status: "warning" },
];

const nodes: Node[] = [
  { id: "node-001", partition: "GPU", status: "healthy", cpu: 45, memory: 60 },
  { id: "node-002", partition: "GPU", status: "healthy", cpu: 78, memory: 82 },
  { id: "node-003", partition: "GPU", status: "warning", cpu: 92, memory: 88 },
  { id: "node-004", partition: "GPU", status: "healthy", cpu: 34, memory: 45 },
  { id: "node-005", partition: "CPU", status: "healthy", cpu: 56, memory: 67 },
  { id: "node-006", partition: "CPU", status: "healthy", cpu: 23, memory: 34 },
  { id: "node-007", partition: "CPU", status: "error", cpu: 0, memory: 0 },
  { id: "node-008", partition: "CPU", status: "healthy", cpu: 67, memory: 71 },
  { id: "node-009", partition: "Memory", status: "healthy", cpu: 45, memory: 89 },
  { id: "node-010", partition: "Memory", status: "warning", cpu: 88, memory: 95 },
  { id: "node-011", partition: "Memory", status: "healthy", cpu: 34, memory: 56 },
  { id: "node-012", partition: "Memory", status: "healthy", cpu: 56, memory: 78 },
];

const PartitionStatus = () => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case "warning":
        return <AlertCircle className="h-4 w-4 text-warning" />;
      case "error":
        return <XCircle className="h-4 w-4 text-destructive" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "bg-success/10 text-success border-success/20";
      case "warning":
        return "bg-warning/10 text-warning border-warning/20";
      case "error":
        return "bg-destructive/10 text-destructive border-destructive/20";
    }
  };

  const getNodeColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "bg-success border-success/40";
      case "warning":
        return "bg-warning border-warning/40";
      case "error":
        return "bg-destructive border-destructive/40";
    }
  };

  return (
    <div className="space-y-6">
      {/* Partition Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Partition Overview</CardTitle>
          <CardDescription>Status of cluster partitions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {partitions.map((partition) => (
              <div
                key={partition.name}
                className="p-4 rounded-lg border border-border bg-card"
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium">{partition.name}</h4>
                  {getStatusIcon(partition.status)}
                </div>
                <p className="text-sm text-muted-foreground mb-3">
                  {partition.nodes} nodes
                </p>
                <Badge variant="outline" className={getStatusColor(partition.status)}>
                  {partition.status}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Node Health Grid */}
      <Card>
        <CardHeader>
          <CardTitle>Node Health Status</CardTitle>
          <CardDescription>Color-coded node health across all partitions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {partitions.map((partition) => {
              const partitionNodes = nodes.filter(
                (node) => node.partition === partition.name.split(" ")[0]
              );
              
              return (
                <div key={partition.name}>
                  <h4 className="font-medium mb-3 text-sm">{partition.name}</h4>
                  <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
                    {partitionNodes.map((node) => (
                      <div
                        key={node.id}
                        className={`p-3 rounded-lg border-2 ${getNodeColor(node.status)} transition-all hover:scale-105 cursor-pointer`}
                        title={`${node.id}\nCPU: ${node.cpu}%\nMemory: ${node.memory}%`}
                      >
                        <div className="text-xs font-medium text-center text-white">
                          {node.id.split("-")[1]}
                        </div>
                        <div className="text-xs text-center text-white/80 mt-1">
                          {node.cpu}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mt-6 pt-4 border-t border-border">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-success border-2 border-success/40" />
              <span className="text-sm text-muted-foreground">Healthy</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-warning border-2 border-warning/40" />
              <span className="text-sm text-muted-foreground">Warning</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-destructive border-2 border-destructive/40" />
              <span className="text-sm text-muted-foreground">Error</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PartitionStatus;
