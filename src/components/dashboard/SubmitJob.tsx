import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Send } from "lucide-react";

const SubmitJob = () => {
  const [jobData, setJobData] = useState({
    name: "",
    nodes: "",
    memory: "",
    timeLimit: "",
    outputPath: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!jobData.name || !jobData.nodes || !jobData.memory || !jobData.timeLimit || !jobData.outputPath) {
      toast.error("Please fill in all fields");
      return;
    }

    (async () => {
      try {
        toast.loading('Submitting job...');

        // Build a minimal sbatch script using the provided fields
        const sbatchLines = [
          '#!/bin/bash',
          `#SBATCH --job-name=${jobData.name}`,
          `#SBATCH --nodes=${jobData.nodes}`,
          `#SBATCH --mem=${jobData.memory}G`,
          `#SBATCH --time=${jobData.timeLimit}:00:00`,
          `#SBATCH --output=${jobData.outputPath}`,
          '',
          '# user commands go here',
          'echo "Hello from job"'
        ];

        const script = sbatchLines.join('\n');

        const resp = await fetch(import.meta.env.VITE_API_BASE || 'http://localhost:8000' + '/api/submit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ script })
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ error: 'Unknown error' }));
          throw new Error(err.error || 'Failed to submit job');
        }

        const result = await resp.json();

        toast.success(`Job "${jobData.name}" submitted successfully! ${result.output || ''}`);
        setJobData({ name: "", nodes: "", memory: "", timeLimit: "", outputPath: "" });

        // Refresh the page so the overview/queue components fetch the latest data.
        // This is a simple approach; a better approach is to lift state or use a shared store.
        setTimeout(() => window.location.reload(), 500);
      } catch (error) {
        console.error('Error submitting job:', error);
        toast.error(error instanceof Error ? error.message : 'Failed to submit job');
      }
    })();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Submit New Job</CardTitle>
        <CardDescription>Configure and submit a new SLURM job to the cluster</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="jobName">Job Name</Label>
              <Input
                id="jobName"
                placeholder="e.g., Neural Network Training"
                value={jobData.name}
                onChange={(e) => setJobData({ ...jobData, name: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="nodes">Number of Nodes</Label>
              <Input
                id="nodes"
                type="number"
                min="1"
                placeholder="e.g., 4"
                value={jobData.nodes}
                onChange={(e) => setJobData({ ...jobData, nodes: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="memory">Memory Requirement (GB)</Label>
              <Input
                id="memory"
                type="number"
                min="1"
                placeholder="e.g., 32"
                value={jobData.memory}
                onChange={(e) => setJobData({ ...jobData, memory: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="timeLimit">Time Limit (hours)</Label>
              <Input
                id="timeLimit"
                type="number"
                min="1"
                placeholder="e.g., 24"
                value={jobData.timeLimit}
                onChange={(e) => setJobData({ ...jobData, timeLimit: e.target.value })}
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="outputPath">Output File Path</Label>
              <Input
                id="outputPath"
                placeholder="/home/user/output/job.out"
                value={jobData.outputPath}
                onChange={(e) => setJobData({ ...jobData, outputPath: e.target.value })}
              />
            </div>
          </div>

          <Button type="submit" className="w-full md:w-auto">
            <Send className="h-4 w-4 mr-2" />
            Submit Job
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};

export default SubmitJob;
