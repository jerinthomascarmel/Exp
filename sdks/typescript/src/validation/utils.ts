
import { FunctionT } from "../types.js";


const EMPTY_OBJECT_JSON_SCHEMA = {
    type: 'object' as const,
    properties: {},
    required:[]
};


class FunctionParser{

    constructor(){}

    parseFunctionJsonSchema(func: Function): Pick<FunctionT , "inputSchema" | "outputSchema" >  {
    
        const resultJsonSchema : Pick<FunctionT , "inputSchema" | "outputSchema"> ={
            inputSchema :EMPTY_OBJECT_JSON_SCHEMA,
            outputSchema : EMPTY_OBJECT_JSON_SCHEMA,
        }
        // return resultJsonSchema;
        
        resultJsonSchema.inputSchema =this._parseFunctionInputSchema(func);
        resultJsonSchema.outputSchema = {
            type:'object' as const,
            properties:{ result : { type : ["string", "number", "integer", "boolean", "array", "object", "null"]}},
            required : ['result']
        }

        return resultJsonSchema;
    }

    _parseFunctionInputSchema(func: Function) : FunctionT["inputSchema"] {
        let resultSchema :FunctionT["inputSchema"] =EMPTY_OBJECT_JSON_SCHEMA;
         const str = func.toString();
         let unknownId = 0 ; 

        // Handle arrow functions, function declarations, and method syntax
        const patterns = [
            /^\s*\w*\s*\(([^)]*)\)/,      // function foo(params)
            /^\([^)]*\)\s*=>/,            // (params) => 
            /^\([^)]*\)\s*\{/,            // (params) => { ... }
            /function\s*\w*\s*\(([^)]*)\)/  // function keyword
        ];


        let match: RegExpMatchArray | null = null;
    
        for (const pattern of patterns) {
            match = str.match(pattern);
            if (match) break;
        }

        if (!match?.[1]) return resultSchema;
        
        const paramStr = match[1].trim();
        if (!paramStr) return resultSchema;

        if (paramStr.startsWith('[') && paramStr.endsWith(']')){
            return resultSchema;
        }

        if (paramStr.startsWith('{') && paramStr.endsWith('}')){
            return resultSchema;
        }

        let parameters =paramStr.split(',')
            .map(param => {
                const trimmed = param.trim();
                if (paramStr.startsWith('[') && paramStr.endsWith(']')){
                    return `unknown${unknownId++}`;
                }

                if (paramStr.startsWith('{') && paramStr.endsWith('}')){
                    return `unknown${unknownId++}`;
                }
                return trimmed;
            });

        parameters.forEach((parameter :string) => {
            resultSchema.properties![parameter] ={type:["string", "number", "integer", "boolean", "array", "object", "null"]}
            resultSchema.required!.push(parameter)
        });

        return resultSchema;
    }
}

export const  functionParser : FunctionParser =new  FunctionParser();