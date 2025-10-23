import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export interface Partition {
	name: string;
	state: string;
	total_nodes: number;
	available_nodes: number;
	total_cpus: number;
	allocated_cpus: number;
	memory?: number;
	max_time?: string;
}

const PartitionStatus = () => {
	const [partitions, setPartitions] = useState<Partition[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		let mounted = true;

		const fetchPartitions = async () => {
			try {
					// Try real partitions endpoint first
					let res = await fetch("/api/partitions");
					let json = null;
					if (res.ok) {
						json = await res.json();
					} else {
						// Fallback to sample resources for dev when partitions endpoint fails
						res = await fetch("/api/debug/sample-resources");
						if (res.ok) json = await res.json();
					}

					if (!mounted) return;
					if (json) {
						// If we got a top-level `partitions` array use it, else try to synthesize from sample-resources
						if (Array.isArray(json.partitions)) {
							setPartitions(json.partitions);
						} else if (Array.isArray(json.partitions)) {
							setPartitions(json.partitions);
						} else if (Array.isArray(json.nodes) && Array.isArray(json.partitions) === false) {
							// synthesize minimal partition entries from sample-resources
							const ps = (json.partitions || []).map((p: any) => ({
								name: p.name,
								state: p.state || 'UNKNOWN',
								total_nodes: p.total_nodes || 0,
								available_nodes: p.available_nodes || 0,
								total_cpus: p.total_cpus || 0,
								allocated_cpus: p.allocated_cpus || 0,
								memory: p.total_memory || p.total_memory || 0,
								max_time: p.max_time || ''
							}));
							// if ps empty, try to build from nodes grouping by partition
							if (ps.length === 0 && Array.isArray(json.nodes)) {
								const map: Record<string, any> = {};
								for (const n of json.nodes) {
									const part = n.partition || 'unknown';
									if (!map[part]) map[part] = { name: part, total_nodes: 0, available_nodes: 0, total_cpus: 0, allocated_cpus: 0, state: 'UNKNOWN' };
									map[part].total_nodes += 1;
									map[part].allocated_cpus += n.cpus_allocated || 0;
									map[part].total_cpus += n.cpus_total || 0;
									if (!n.state || n.state === 'idle') map[part].available_nodes += 1;
								}
								setPartitions(Object.values(map));
							} else {
								setPartitions(ps);
							}
						}
					}
			} catch (e) {
				console.error("Failed to load partitions:", e);
				if (mounted) setError("Failed to load partition information");
			} finally {
				if (mounted) setLoading(false);
			}
		};

		fetchPartitions();
		const id = setInterval(fetchPartitions, 30000);
		return () => {
			mounted = false;
			clearInterval(id);
		};
	}, []);

	const getStatusIcon = (state: string, cpuPct: number) => {
		const up = String(state ?? "").toUpperCase().startsWith("UP");
		if (!up) return <XCircle className="h-4 w-4 text-destructive" />;
		if (cpuPct >= 90) return <AlertCircle className="h-4 w-4 text-warning" />;
		return <CheckCircle2 className="h-4 w-4 text-success" />;
	};

	const getStatusColor = (state: string, cpuPct: number) => {
		const up = String(state ?? "").toUpperCase().startsWith("UP");
		if (!up) return "bg-destructive/10 text-destructive border-destructive/20";
		if (cpuPct >= 90) return "bg-warning/10 text-warning border-warning/20";
		return "bg-success/10 text-success border-success/20";
	};

		return (
			<div className="space-y-6">
				<div className="flex items-center justify-between">
					<div className="text-sm text-muted-foreground">Partitions: <strong>{partitions.length}</strong></div>
					{loading && <div className="text-sm">Refreshing...</div>}
				</div>
				{error && <div className="text-center text-destructive">{error}</div>}

			<Card>
				<CardHeader>
					<CardTitle>Partition Overview</CardTitle>
					<CardDescription>Status of cluster partitions</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="grid grid-cols-1 gap-4">
						{partitions.length === 0 && !loading && <div>No partitions found</div>}

						{partitions.map((p) => {
							const totalCpus = p.total_cpus || 0;
							const allocated = p.allocated_cpus || 0;
							const cpuPct = totalCpus > 0 ? Math.round((allocated / totalCpus) * 100) : 0;
							const totalNodes = p.total_nodes || 0;
							const available = typeof p.available_nodes === "number" ? p.available_nodes : totalNodes;
							const nodePct = totalNodes > 0 ? Math.round(((totalNodes - available) / totalNodes) * 100) : 0;

							return (
								<div key={p.name} className="p-4 rounded-lg border border-border bg-card">
									<div className="flex items-center justify-between mb-2">
										<h4 className="font-medium">{p.name}</h4>
										{getStatusIcon(p.state, cpuPct)}
									</div>

									<p className="text-sm text-muted-foreground mb-2">
										{totalNodes} nodes ({available} available)
									</p>

									<div className="space-y-3">
										<div>
											<div className="flex justify-between text-sm mb-1">
												<span>CPU Usage</span>
												<span>{cpuPct}%</span>
											</div>
											<Progress value={cpuPct} className="h-2" />
										</div>

										<div>
											<div className="flex justify-between text-sm mb-1">
												<span>Node Usage</span>
												<span>{nodePct}%</span>
											</div>
											<Progress value={nodePct} className="h-2" />
										</div>
									</div>

									<div className="mt-3">
										<Badge variant="outline" className={getStatusColor(p.state, cpuPct)}>
											{String(p.state ?? "").toUpperCase().startsWith("UP") ? (cpuPct >= 90 ? "BUSY" : "AVAILABLE") : p.state}
										</Badge>
									</div>

									{p.max_time && (
										<p className="text-xs text-muted-foreground mt-2">Max Time: {p.max_time}</p>
									)}
								</div>
							);
						})}
					</div>
				</CardContent>
			</Card>
		</div>
	);
};

export default PartitionStatus;


