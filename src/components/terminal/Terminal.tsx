import { useEffect, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TerminalProps {
  onClose: () => void;
}

const Terminal = ({ onClose }: TerminalProps) => {
  const [output, setOutput] = useState<string[]>([
    "Connecting to SLURM cluster...",
    "Resources allocated successfully",
    "Starting interactive session...",
    ""
  ]);
  const [input, setInput] = useState("");
  const outputRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
    inputRef.current?.focus();
  }, [output]);

  const handleCommand = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && input.trim()) {
      const newOutput = [...output, `$ ${input}`];
      
      // Simulate command responses
      if (input.toLowerCase() === "exit") {
        onClose();
        return;
      } else if (input.toLowerCase() === "ls") {
        newOutput.push("file1.txt  file2.txt  script.sh");
      } else if (input.toLowerCase().startsWith("echo ")) {
        newOutput.push(input.substring(5));
      } else {
        newOutput.push(`bash: ${input}: command not found`);
      }
      
      newOutput.push("");
      setOutput(newOutput);
      setInput("");
    }
  };

  return (
    <Card className="bg-black border-muted overflow-hidden">
      <div className="flex items-center justify-between bg-muted/20 px-4 py-2 border-b border-muted">
        <span className="text-sm font-mono text-muted-foreground">user@hpc-cluster:~</span>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-6 w-6 hover:bg-destructive/20"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      
      <div
        ref={outputRef}
        className="h-96 overflow-y-auto p-4 font-mono text-sm"
      >
        {output.map((line, i) => (
          <div key={i} className="text-green-400">
            {line}
          </div>
        ))}
        
        <div className="flex items-center gap-2">
          <span className="text-green-400">$</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleCommand}
            className="flex-1 bg-transparent outline-none text-green-400 font-mono"
            autoFocus
          />
        </div>
      </div>
    </Card>
  );
};

export default Terminal;
