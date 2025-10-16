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
];

const nodes: Node[] = [
  { id: "node-001", partition: "GPU", status: "healthy", cpu: 45, memory: 60 },
  { id: "node-002", partition: "GPU", status: "healthy", cpu: 78, memory: 82 },
  { id: "node-003", partition: "GPU", status: "warning", cpu: 92, memory: 88 },
  { id: "node-004", partition: "GPU", status: "healthy", cpu: 34, memory: 45 },
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
          <div className="grid grid-cols-1 gap-4">
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

    </div>
  );
};

export default PartitionStatus;
