import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Send, Upload, Loader2 } from "lucide-react";
import Terminal from "@/components/terminal/Terminal";

const SubmitJob = () => {
  const [mode, setMode] = useState<"sbatch" | "alloc">("sbatch");
  const [loading, setLoading] = useState(false);
  const [showTerminal, setShowTerminal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobData, setJobData] = useState({
    name: "",
    nodes: "",
    memory: "",
    timeLimit: "",
  });

  const handleSbatchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile) {
      toast.error("Please select a batch script file");
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('username', 'testuser'); // TODO: Replace with actual username
      formData.append('file', selectedFile);

      const response = await fetch('http://localhost:8000/api/submit/sbatch', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to submit job');
      }

      const data = await response.json();
      toast.success(`Job submitted successfully! Job ID: ${data.job_id}`);
      setSelectedFile(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to submit job');
    } finally {
      setLoading(false);
    }
  };

  const handleAllocSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!jobData.name || !jobData.nodes || !jobData.timeLimit) {
      toast.error("Please fill in all required fields (Job Name, Nodes, Time Limit)");
      return;
    }

    setLoading(true);
    try {
      // Build request body, omitting memory if blank
      const reqBody: any = {
        username: 'testuser', // TODO: Replace with actual username
        nodes: parseInt(jobData.nodes),
        time: parseInt(jobData.timeLimit),
        jobName: jobData.name
      };
      if (jobData.memory && jobData.memory.trim() !== "") {
        reqBody.memory = parseInt(jobData.memory);
      }
      const response = await fetch('http://localhost:8000/api/submit/salloc', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(reqBody)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to allocate resources');
      }

      const data = await response.json();
      
      if (data.session_id) {
        console.log('Received session ID:', data.session_id);
        toast.success("Resources allocated successfully!");
        // Store the session ID for the terminal component to use
        localStorage.setItem('currentTerminalSession', data.session_id);
        console.log('Stored session ID in localStorage');
        setShowTerminal(true);
        setJobData({ name: "", nodes: "", memory: "", timeLimit: "" });
      } else {
        console.error('No session_id in response:', data);
        throw new Error('No session ID returned from server');
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to allocate resources');
      setShowTerminal(false);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  if (showTerminal) {
    return (
      <div className="space-y-4">
        <Button variant="outline" onClick={() => setShowTerminal(false)}>
          Back to Submit Job
        </Button>
        <Terminal onClose={() => setShowTerminal(false)} />
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Submit New Job</CardTitle>
        <CardDescription>Configure and submit a new SLURM job to the cluster</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-center gap-1 p-1 bg-muted rounded-lg max-w-md mx-auto">
          <button
            type="button"
            onClick={() => setMode("sbatch")}
            className={`flex-1 py-3 px-6 rounded-md font-medium text-sm transition-all duration-300 ${
              mode === "sbatch"
                ? "bg-primary text-primary-foreground shadow-lg scale-105"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}
          >
            SBATCH
          </button>
          <button
            type="button"
            onClick={() => setMode("alloc")}
            className={`flex-1 py-3 px-6 rounded-md font-medium text-sm transition-all duration-300 ${
              mode === "alloc"
                ? "bg-primary text-primary-foreground shadow-lg scale-105"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}
          >
            SALLOC
          </button>
        </div>

        {mode === "sbatch" ? (
          <form onSubmit={handleSbatchSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="batchFile">Batch Script File</Label>
              <div className="flex items-center gap-4">
                <Input
                  id="batchFile"
                  type="file"
                  accept=".sh,.slurm,.sbatch"
                  onChange={handleFileChange}
                  className="cursor-pointer"
                />
              </div>
              {selectedFile && (
                <p className="text-sm text-muted-foreground">
                  Selected: {selectedFile.name}
                </p>
              )}
            </div>

            <Button type="submit" className="w-full md:w-auto" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Submitting Job...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Submit Batch Job
                </>
              )}
            </Button>
          </form>
        ) : (
          <form onSubmit={handleAllocSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="jobName">Job Name</Label>
                <Input
                  id="jobName"
                  placeholder="e.g., Interactive Session"
                  value={jobData.name}
                  onChange={(e) => setJobData({ ...jobData, name: e.target.value })}
                  disabled={loading}
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
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="memory">Memory Requirement (GB, optional)</Label>
                <Input
                  id="memory"
                  type="number"
                  min=""
                  placeholder="Leave blank for auto allocation"
                  value={jobData.memory}
                  onChange={(e) => setJobData({ ...jobData, memory: e.target.value })}
                  disabled={loading}
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
                  disabled={loading}
                />
              </div>
            </div>

            <Button type="submit" className="w-full md:w-auto" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Allocating Resources...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Submit & Start Session
                </>
              )}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
};

export default SubmitJob;
