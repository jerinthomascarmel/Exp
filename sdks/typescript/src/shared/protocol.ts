import { Transport } from "./transport.js";
import {  JSONRPCResponse ,  McpError, ErrorCode,
        JSONRPCRequest, Result, JSONRPCError ,
        isJSONRPCResponse , isJSONRPCError , isJSONRPCRequest,
        Request} from "../types.js";

import { ZodType, z , ZodObject , ZodLiteral} from "zod";



export abstract class Protocol {

    private _transport? : Transport;
    private _requestMessageId = 0;
    private _responseHandlers: Map<number,(response: JSONRPCResponse | Error) => void> = new Map();
    private _requestHandlers: Map<string,(request: JSONRPCRequest) => Promise<Result>> = new Map();
    

    onclose? :() => void; 
    onerror? :(error :Error) => void; 

    constructor(_transport: Transport){
        this._transport = _transport;
    }


    async connect() {
        if(!this._transport){
            throw new Error("Initialize Transport first !");
        }
        this._transport.onclose = () => this._onclose();
        this._transport.onerror = (error) => this._onerror(error);
        this._transport.onmessage = (message) =>{
            
            if (isJSONRPCResponse(message) || isJSONRPCError(message)){
                this._onresponse(message);
            }else if(isJSONRPCRequest(message)){
                this._onrequest(message); 
            }else{
                this._onerror(new Error(`Unknown message type: ${JSON.stringify(message)}`))
            }
        }

        await this._transport.start();
    }

    private _onclose(): void {
        const responseHandlers = this._responseHandlers;
        this._responseHandlers = new Map();

        this._transport = undefined;
        this.onclose?.();
   

        const error = new McpError(ErrorCode.ConnectionClosed, "Connection closed");
        for (const handler of responseHandlers.values()) {
            handler(error);
        }
    }

    private _onerror(error: Error): void {
        this.onerror?.(error);
    }

    private _onrequest(request: JSONRPCRequest): void {
        const handler =this._requestHandlers.get(request.method);

        // Capture the current transport at request time to ensure responses go to the correct client
        const capturedTransport = this._transport;

        if (handler === undefined) {
            capturedTransport
                ?.send({
                    jsonrpc: "2.0",
                    id: request.id,
                    error: {
                        code: ErrorCode.MethodNotFound,
                        message: "Method not found",
                    },
                })
                .catch((error) =>
                this._onerror(
                    new Error(`Failed to send an error response: ${error}`),
                ),
                );
            return;
        }

        
        // Starting with Promise.resolve() puts any synchronous errors into the monad as well.
        Promise.resolve()
        .then(() => handler(request))
        .then(
            (result) => {
            
            return capturedTransport?.send({
                result,
                jsonrpc: "2.0",
                id: request.id,
            });
            },
            (error) => {
            
            return capturedTransport?.send({
                jsonrpc: "2.0",
                id: request.id,
                error: {
                code: Number.isSafeInteger(error["code"])
                    ? error["code"]
                    : ErrorCode.InternalError,
                message:error.message ??  "Internal error",
                },
            });
            },
        )
        .catch((error) =>
            this._onerror(new Error(`Failed to send response: ${error}`)),
        )
    }

    private _onresponse(response: JSONRPCResponse | JSONRPCError): void {
        const messageId = Number(response.id);
        const handler = this._responseHandlers.get(messageId);
        if (handler === undefined) {
            this._onerror(
                    new Error(
                    `Received a response for an unknown message ID: ${JSON.stringify(response)}`,
                    ),
                );
            return;
        }

        this._responseHandlers.delete(messageId);
        console.log('response' , response)

        if (isJSONRPCResponse(response)) {
            handler(response);
        } else {
        const error = new McpError(
            response.error.code,
            response.error.message,
            response.error.data,
        );
            handler(error);
        }
    }

     /**
     * Closes the connection.
     */
    async close(): Promise<void> {
        await this._transport?.close();
    }

    /**
     * Sends a request and wait for a response.
     *
     * Do not use this method to emit notifications! Use notification() instead.
     */
    request<T extends ZodType<object>>(
        request: Request,
        resultSchema: T
    ): Promise<z.infer<T>> {

        return new Promise((resolve, reject) => {
            if (!this._transport) {
                reject(new Error("Not connected"));
                return;
            }

            const messageId = this._requestMessageId++;
            const jsonrpcRequest: JSONRPCRequest = {
                ...request,
                jsonrpc: "2.0",
                id: messageId
            };


            this._responseHandlers.set(messageId, (response) => {
                
                if (response instanceof Error) {
                    return reject(response);
                }


                try {
                    const result = resultSchema.parse(response.result);
                    resolve(result);
                } catch (error) {
                    reject(error);
                }
            });

       
            this._transport.send(jsonrpcRequest).catch((error) => {
                reject(error);
            });
        });
    }


    /**
   * Registers a handler to invoke when this protocol object receives a request with the given method.
   *
   * Note that this will replace any previous request handler for the same method.
   */
  setRequestHandler<
    T extends ZodObject<{
      method: ZodLiteral<string>;
    }>,
  >(
    requestSchema: T,
    handler: (
      request: z.infer<T>   
    ) => Result | Promise<Result>,
  ): void {
    
    const method = requestSchema.shape.method.value;

    this._requestHandlers.set(method, (request) => {
      return Promise.resolve(handler(requestSchema.parse(request)));
    });
  }

}