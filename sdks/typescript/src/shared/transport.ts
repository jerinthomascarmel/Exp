import { JSONRPCMessage } from "../types.js";


export interface Transport {

    // start connection 
    start(): Promise<void>;

    /**
     * Sends a JSON-RPC message (request or response).
     *
     * If present, `relatedRequestId` is used to indicate to the transport which incoming request to associate this outgoing message with.
     */
    send(message: JSONRPCMessage): Promise<void>;

    //close connection 
    close(): Promise<void>;

    /**
     * Callback for when the connection is closed for any reason.
     *
     * This should be invoked when close() is called as well.
     */
    onclose?: () => void;

    /**
     * Callback for when an error occurs.
     *
     * Note that errors are not necessarily fatal; they are used for reporting any kind of exceptional condition out of band.
     */
    onerror?: (error: Error) => void;

    //call back when a message (request or response) is received over the connection
    onmessage?: (message:JSONRPCMessage) => void; 

}