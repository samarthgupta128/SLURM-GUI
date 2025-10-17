const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export interface Job {
  job_id: string;
  name: string;
  user: string;
  state: string;
  time: string;
  nodes: string;
  reason: string;
}

export interface Node {
  name: string;
  state: string;
  cpus_allocated: number;
  cpus_idle: number;
  cpus_offline: number;
  cpus: number;
  memory_allocated: number | null;
  memory: string;
}

export interface SubmitJobParams {
  name: string;
  nodes: string;
  memory: string;
  timeLimit: string;
  outputPath: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async getQueue(): Promise<Job[]> {
    const response = await fetch(`${this.baseUrl}/api/queue`);
    if (!response.ok) {
      throw new Error('Failed to fetch job queue');
    }
    const data = await response.json();
    return data.jobs;
  }

  async getUsage(): Promise<Node[]> {
    const response = await fetch(`${this.baseUrl}/api/usage`);
    if (!response.ok) {
      throw new Error('Failed to fetch cluster usage');
    }
    const data = await response.json();
    return data.nodes;
  }

  async submitJob(params: SubmitJobParams): Promise<{ message: string; output: string }> {
    const script = `#!/bin/bash
#SBATCH --job-name=${params.name}
#SBATCH --nodes=${params.nodes}
#SBATCH --mem=${params.memory}G
#SBATCH --time=${params.timeLimit}:00:00
#SBATCH --output=${params.outputPath}

srun hostname
`;

    const formData = new FormData();
    formData.append('script', script);

    const response = await fetch(`${this.baseUrl}/api/submit`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error('Failed to submit job');
    }

    return response.json();
  }

  async cancelJob(jobId: string): Promise<{ result: string }> {
    const response = await fetch(`${this.baseUrl}/api/cancel/${jobId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new Error('Failed to cancel job');
    }

    return response.json();
  }
}

export const api = new ApiClient();