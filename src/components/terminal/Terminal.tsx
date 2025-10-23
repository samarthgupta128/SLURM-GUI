import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";
import { Card } from "@/components/ui/card";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TerminalProps {
  onClose: () => void;
}

const Terminal = ({ onClose }: TerminalProps) => {
  const [output, setOutput] = useState<string[]>(["Connecting to SLURM cluster..."]);
  const [input, setInput] = useState("");
  const outputRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const socketRef = useRef<Socket | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const sessionId = localStorage.getItem('currentTerminalSession');
    if (!sessionId) {
      setOutput(prev => [...prev, "Error: No session ID found"]);
      return;
    }

    console.log('Attempting to connect to socket.io with session:', sessionId);
    // Let socket.io-client choose transports (polling -> websocket if available).
    const socket = io('http://localhost:8000', {
      reconnectionAttempts: 10,
      timeout: 20000,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('socket.io connected', socket.id);
      setConnected(true);
      socket.emit('terminal_connect', { session_id: sessionId });
      setOutput(prev => [...prev, 'Connected to terminal session']);
    });

    socket.on('terminal_connected', (d: any) => {
      console.log('terminal_connected', d);
    });

    socket.on('terminal_output', (d: any) => {
      if (d && d.output) setOutput(prev => [...prev, d.output]);
    });

    socket.on('terminal_error', (d: any) => {
      if (d && d.error) setOutput(prev => [...prev, `Error: ${d.error}`]);
    });

    socket.on('disconnect', () => {
      setConnected(false);
      setOutput(prev => [...prev, 'Disconnected from terminal session']);
    });

    socket.on('connect_error', (err: any) => {
      console.error('socket connect_error', err);
      setOutput(prev => [...prev, 'Error: Failed to connect to terminal']);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
    inputRef.current?.focus();
  }, [output]);

  const handleCommand = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && input.trim()) {
      if (!socketRef.current || !socketRef.current.connected) {
        setOutput(prev => [...prev, "Error: Not connected to terminal"]);
        return;
      }

      setOutput(prev => [...prev, `$ ${input}`]);
      
      if (input.toLowerCase() === "exit") {
        socketRef.current.disconnect();
        onClose();
        return;
      }

      // Send command to server using Socket.IO emit
      socketRef.current.emit('terminal_input', {
        input: input + '\n',
        session_id: localStorage.getItem('currentTerminalSession')
      });
      
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
