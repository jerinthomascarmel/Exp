
import { FunctionT } from "../types.js";


const EMPTY_OBJECT_JSON_SCHEMA = {
    type: 'object' as const,
    properties: {},
    required:[]
};


class FunctionParser{

    constructor(){}

    parseFunctionJsonSchema(func: (args:Record<string , any>)=>any ): Pick<FunctionT , "inputSchema" | "outputSchema" >  {
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

    _parseFunctionInputSchema(func: (args:Record<string , any>)=>any ) : FunctionT["inputSchema"] {
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
        
        let paramStr = match[1].trim();
        if (!paramStr) return resultSchema;

        if (!(paramStr.startsWith('{') && paramStr.endsWith('}'))){
            throw new Error("must be an object with key , value as argument name and value !");
        }

       
        paramStr = paramStr.slice(1,paramStr.length);

        paramStr.split(',')
            .forEach(param => {
                const trimmed = param.trim();
                if(trimmed.includes(":")){
                    // resultSchema.properties![trimmed] = {type: "object"}

                }else{
                    resultSchema.properties![trimmed] = {type:["string", "number", "integer", "boolean", "array", "object", "null"]}
                    resultSchema.required!.push(trimmed);
                    return trimmed;
                }
            });

        // parameters.forEach((parameter :string) => {
        //     resultSchema.properties![parameter] ={type:["string", "number", "integer", "boolean", "array", "object", "null"]}
        //     resultSchema.required!.push(parameter)
        // });

        return resultSchema;
    }
}

export const  functionParser : FunctionParser =new  FunctionParser();