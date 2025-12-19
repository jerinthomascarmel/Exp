import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";
import type { JsonSchemaType } from "../validation/types.js";
import { Protocol  } from "../shared/protocol.js";

import 
    { 
        CallFunctionRequestSchema,
        CallFunctionResult,
        ErrorCode,
        McpError ,
        ListFunctionsResult,
        ListFunctionsRequestSchema ,
        FunctionT,
        InitializeRequestSchema,
        InitializeResult
    } from "../types.js";
import { StdioExporterTransport } from "../exporter/stdio.js";
import { functionParser } from "../validation/utils.js";
import { jsonSchemaValidator } from "../validation/types.js";
import { AjvJsonSchemaValidator } from "../validation/ajv-provider.js";



export class Exporter extends Protocol{

    private registeredFunctions : { [name : string] : RegisterFunction} ={};
    private _jsonSchemaValidator : jsonSchemaValidator = new AjvJsonSchemaValidator();

    constructor(){
        super(new StdioExporterTransport());
        this.setInitializeRequestHandlers();
        this.setFunctionRequestHandlers(); 
    }


    async connect(): Promise<void> {
        await super.connect();
    }

    // decorators 
    export(fn : (args: Record<string, any>) =>any ){
        // check the descriptor.value is a function or not. 
        if(!fn || typeof fn != 'function'){
            return fn;
        }

        let toolName = (fn as Function).name;
        let jsonSchema = functionParser.parseFunctionJsonSchema(fn);
        this.registerFunction(
            toolName,
            {
                inputSchema: jsonSchema["inputSchema"],
                outputSchema : jsonSchema["outputSchema"]
            },
            fn
        )
            
    }

    registerFunction(
        name:string, 
        config : {
            description?: string;
            inputSchema?: z.ZodTypeAny | FunctionT["inputSchema"];
            outputSchema?:  z.ZodTypeAny  | FunctionT["outputSchema"];
        },
        cb: Function
        ):void {

        if (this.registeredFunctions[name]) {
            throw new Error(`Function ${name} is already registered`);
        }

        const { description, inputSchema, outputSchema } = config;

        let inputJsonSchema : FunctionT["inputSchema"] =( inputSchema ? 
                                (inputSchema instanceof z.ZodType ? zodToJsonSchema(inputSchema): inputSchema)
                                : EMPTY_OBJECT_JSON_SCHEMA) as FunctionT["inputSchema"]
                                
        let outputJsonSchema = (outputSchema ? 
                                (outputSchema instanceof z.ZodType ? zodToJsonSchema(outputSchema): outputSchema)
                                : EMPTY_OBJECT_JSON_SCHEMA) as FunctionT["outputSchema"]

        const registeredFunction :RegisterFunction = {
            name: name , 
            description:description, 
            inputSchema: inputJsonSchema, 
            outputSchema : outputJsonSchema,
            callback:cb
        }

        this.registeredFunctions[name] = registeredFunction;
    }


    async listRegisteredFunctions():Promise<RegisterFunction[]>{
        return Object.values(this.registeredFunctions);
    }

    private getFunctionSchemas():ListFunctionsResult["functions"]{
        return Object.entries(this.registeredFunctions).map(([name , fn]):FunctionT=>{
                    const functionObj :FunctionT = {
                        name,
                        inputSchema: fn.inputSchema,
                        outputSchema: fn.outputSchema
                    }
                    return functionObj;
                });
    }

    private setInitializeRequestHandlers(){
        this.setRequestHandler(
            InitializeRequestSchema,
            (): InitializeResult =>{
                
                return ({
                capabilities:{
                    functions: Object.fromEntries(
                        Object.entries(this.registeredFunctions).map(([key , value])=>[
                            key,
                            {name:value.name, inputSchema: value.inputSchema , outputSchema:value.outputSchema}
                        ]) 
                    ), 
                    classes : {}
                }
            })}
        )
    }

    private setFunctionRequestHandlers() {
        this.setRequestHandler(
            ListFunctionsRequestSchema,
            (): ListFunctionsResult =>({
                functions: this.getFunctionSchemas()
            })
        )

        this.setRequestHandler(
        CallFunctionRequestSchema,
        async (request): Promise<CallFunctionResult> => {
            const fn = this.registeredFunctions[request.params.name];
            
            if (!fn) {
                throw new McpError(
                    ErrorCode.InvalidParams,
                    `Function ${request.params.name} not found`,
                );
            }

            // throw new McpError(
            //     ErrorCode.InvalidParams,
            //     `Function input shcema : ${JSON.stringify(fn.inputSchema)}`
            // )

            let result: CallFunctionResult;            
            const inputValidator = this._jsonSchemaValidator.getValidator(fn.inputSchema as JsonSchemaType)

            if(!inputValidator) throw new McpError(ErrorCode.InvalidParams , 'input validator not found . '); 
            
            try{
                const inputValidationResult= inputValidator(request.params.arguments);
                if (!inputValidationResult.valid) {
                    throw new McpError(
                    ErrorCode.InvalidParams,
                    `Invalid arguments for function ${request.params.name}: ${inputValidationResult.errorMessage}`,
                    );
                }
            }catch (error) {
                if (error instanceof McpError) {
                    throw error;
                }
                throw new McpError(
                    ErrorCode.InvalidParams,
                    `Failed to validate structured content: ${error instanceof Error ? error.message : String(error)}`
                );
            }
            
        
            const args = request.params.arguments;
            const cb = fn.callback as Function;
            let  cbResult : any |  Promise<any> ;
            try {
                cbResult = await Promise.resolve(cb(...(args ? Object.values(args) : [])));

                result = {
                    content:[ { type:"text" , text : "result is in structured Result"}], 
                    structuredResult: { result:cbResult}, 
                    isError: false
                }

                

            } catch (error) {
                
                result = {
                    content: [
                        {
                            type: "text",
                            text: error instanceof Error ? error.message : String(error),
                        },
                    ],
                    isError: true,
                };
            }

            const outputValidator = this._jsonSchemaValidator.getValidator(fn.outputSchema! as JsonSchemaType)
            if(!outputValidator) throw new McpError(ErrorCode.InvalidParams , 'input validator not found .'); 
            try{
                const outputValidationResult= outputValidator(result.structuredResult);
                if (!outputValidationResult.valid) {
                    throw new McpError(
                    ErrorCode.InvalidParams,
                    `Invalid arguments for function ${request.params.name}: ${outputValidationResult.errorMessage}`,
                    );
                }
            }catch (error) {
                if (error instanceof McpError) {
                    throw error;
                }
                throw new McpError(
                    ErrorCode.InvalidRequest,
                    `Failed to validate structured content: ${error instanceof Error ? error.message : String(error)}`
                );
            }

            return result;
        });

    }

}


const EMPTY_OBJECT_JSON_SCHEMA = {
    type: 'object' as const,
    properties: {}
};

export type RegisterFunction = {
    name: string; 
    description?: string;
    inputSchema: FunctionT["inputSchema"]
    outputSchema: FunctionT["outputSchema"];
    callback:Function;
}


