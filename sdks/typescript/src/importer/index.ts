import { Protocol } from "../shared/protocol.js";

import { CallFunctionRequest ,
    CallFunctionResultSchema ,
    CompatibilityCallToolResultSchema,
    ErrorCode ,
    McpError ,
    ListFunctionsResultSchema,
    InitializeResultSchema,
    ServerCapabilities,
    } from "../types.js";

import { StdioImporterTransport } from "../importer/stdio.js";
import { StdioParameters } from "../importer/stdio.js";

export class Importer extends Protocol{
    private _serverCapabilities?: ServerCapabilities;
   
    constructor(params: StdioParameters){
        super(new StdioImporterTransport(params)) ;
    }

    async connect() {
        await super.connect(); 
        // additional setup for Importer can be done here
        try{
            const result = await this.request(
                {
                    method: "initialize",
                    params: {}
                },
                InitializeResultSchema
            )

            if (result === undefined) {
                throw new Error(`Server sent invalid initialize result: ${result}`);
            }

            this._serverCapabilities = result.capabilities;

        
        }catch(error){
            void this.close();
            throw error;

        }
    }

    async callFunction(name:CallFunctionRequest["params"]["name"]){
        const func = async (args:CallFunctionRequest["params"]["arguments"])=>{
            
            const result = await this.request({ method: "functions/call" ,
                                                params: {name:name ,arguments:args } } ,
                                                CallFunctionResultSchema);

            if(result.isError){
                throw new McpError(
                ErrorCode.InvalidRequest,
                `Function ${name} has an output schema but did not return structured content`);
            }

            if(!result.structuredResult){
                throw new McpError(
                    ErrorCode.ParseError,
                    `Function never return anything`
                )
            }

            return result.structuredResult;
        }

        return func;
        
    }

    async getFunction(name:string){
        return this.callFunction(name);
    }

    async listFunctions(){
        if(this._serverCapabilities){
            return this._serverCapabilities.functions;
        }
        const result = await this.request({ method: "functions/list" , params:{} } ,ListFunctionsResultSchema);
        return result.functions; 
    }
}
