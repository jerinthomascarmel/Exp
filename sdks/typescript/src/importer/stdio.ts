import { Transport } from "../shared/transport.js";
import { JSONRPCMessage } from "../types.js";
import spawn from "cross-spawn";
import { ChildProcess } from "node:child_process";
import { ReadBuffer , serializeMessage } from "../shared/stdio.js";


export type StdioParameters = {
  /**
   * The executable to run to start the server.
   */
  command: string;

  /** 
   * Command line arguments to pass to the executable.
   */
  args?: string[];

  /**
   * The working directory to use when spawning the process.
   *
   * If not specified, the current working directory will be inherited.
   */
  cwd?: string;
};


export class StdioImporterTransport implements Transport{

    private _process?: ChildProcess;
    private _params: StdioParameters;
    private _abortController: AbortController = new AbortController();
    private _readBuffer: ReadBuffer = new ReadBuffer();

    
    onclose?: () => void;
    onerror?: (error: Error) => void;
    onmessage?: (message: JSONRPCMessage) => void;

    constructor(server: StdioParameters) {
      this._params = server;  
    }


    /**
     * Starts the server process and prepares to communicate with it.
     */
    async start(): Promise<void> {
      if (this._process) {
        throw new Error(
          "StdioClientTransport already started! If using Client class, note that connect() calls start() automatically."
        );
      }

      return new Promise((resolve, reject) => {
        this._process = spawn(
          this._params.command,
          this._params.args ?? [],
          {
            stdio: ["pipe", "pipe", "inherit"],
            shell: false,
            signal: this._abortController.signal,
            windowsHide: process.platform === "win32" && isElectron(),
            cwd: this._params.cwd
          }
        );

        this._process.on("error", (err) => {
          if(err.name ==="AbortError") {
            this.onclose?.();
            return ;
          }
          reject(err);
          this.onerror?.(err);
        });


        this._process.on("spawn", () => {
          resolve();
        });

        this._process.on("close", (_code) => {
          this._process = undefined;
          this.onclose?.();
        });

        this._process.stdin?.on("error", (error) => {
          this.onerror?.(error);
        });


        this._process.stdout?.on("data", (chunk) => {
          this._readBuffer.append(chunk);
          this.processReadBuffer();
        });

        this._process.stdout?.on("error", (error) => {
          this.onerror?.(error);
        });

      });
    }

    
    /**
     * The child process pid spawned by this transport.
     *
     * This is only available after the transport has been started.
     */
    get pid(): number | null {
      return this._process?.pid ?? null;
    }


    private processReadBuffer() {
      while (true) {
        try {
          const message = this._readBuffer.readMessage();
          if (message === null) {
            break;
          }

          this.onmessage?.(message);
        } catch (error) {
          this.onerror?.(error as Error);
        }
      }
    }

    async close(): Promise<void> {
      this._abortController.abort();
      this._process = undefined;
      this._readBuffer.clear();
    }


    send(message: JSONRPCMessage): Promise<void> {
      return new Promise((resolve) => {
        if (!this._process?.stdin) {
          throw new Error("Not connected");
        }

        const json = serializeMessage(message);
        if (this._process.stdin.write(json)) {
          resolve();
        } else {
          this._process.stdin.once("drain", resolve);
        }
      });
    }

}

function isElectron() {
  return "type" in process;
}