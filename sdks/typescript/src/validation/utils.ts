
import { FunctionT } from "../types.js";

enum Divider { 
    comma = "," , 
    colon = ":"
}


class FunctionParser{
    EMPTY_OBJECT_JSON_SCHEMA = {
        type: 'object' as const,
        properties: {},
        required: []
    };

    constructor(){}

    parseFunctionJsonSchema<FnArgs extends Record<string, any>> (func: (args:FnArgs)=>any ): Pick<FunctionT , "inputSchema" | "outputSchema" >  {
        const resultJsonSchema : Pick<FunctionT , "inputSchema" | "outputSchema"> ={
            inputSchema :{ ...this.EMPTY_OBJECT_JSON_SCHEMA , properties: {} , required: [] },
            outputSchema : { ...this.EMPTY_OBJECT_JSON_SCHEMA , properties: {} , required: [] }
        }
        // return resultJsonSchema;
        
        resultJsonSchema.inputSchema =this._parseFunctionInputSchema(func);
        resultJsonSchema.outputSchema = {
            type:'object' as const,
            properties:{ result : {}},
            required : ['result']
        }

        return resultJsonSchema;
    }

    _parseFunctionInputSchema<FnArgs extends Record<string,any>>(func: (args:FnArgs)=>any ) : FunctionT["inputSchema"] {
        let resultSchema :FunctionT["inputSchema"] ={ ...this.EMPTY_OBJECT_JSON_SCHEMA , properties: {} , required: [] }

         const str = func.toString();
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


        paramStr = paramStr.slice(1,paramStr.length-1);
        const params = this._splitBy(paramStr,Divider.comma);

    
        params.forEach(param => {
                const trimmed = param.trim();
                if(trimmed.includes(":")){
                    let [ key , value , ...rest ] =  this._splitBy(trimmed , Divider.colon);
                    resultSchema.properties![key] = this._parseUtil(value);
                    resultSchema.required!.push(key);
                }else{
                    resultSchema.properties![trimmed] = {}
                    resultSchema.required!.push(trimmed);
                    return trimmed;
                }
            });

        return resultSchema;
    }

    _parseUtil(objectStr : string) :FunctionT["inputSchema"]{
        let resultSchema:FunctionT["inputSchema"] = { ...this.EMPTY_OBJECT_JSON_SCHEMA , properties: {} , required: [] }

        objectStr = objectStr.trim();
        objectStr = objectStr.slice(1,objectStr.length-1);
        const params = this._splitBy(objectStr,Divider.comma);
        
        params.forEach(param => {
                const trimmed = param.trim();
                if(trimmed.includes(":")){
                    let [ key , value , ...rest ] =  this._splitBy(trimmed , Divider.colon);
                    resultSchema.properties![key] = this._parseUtil(value);
                    resultSchema.required!.push(key);
                }else{
                    resultSchema.properties![trimmed] = {}
                    resultSchema.required!.push(trimmed);
                    return trimmed;
                }
            });

        return resultSchema;
    }

    // NEW: Smart comma splitter that respects nesting
    _splitBy(str: string, divider : Divider): string[] {
        const result: string[] = [];
        let current = '';
        let depth = 0;

        for (let i = 0; i < str.length; i++) {
            const char = str[i];

            if (char === '{' || char === '[' || char === '(') {
                depth++;
                current += char;
            } else if (char === '}' || char === ']' || char === ')') {
                depth--;
                current += char;
            } else if (char === divider  && depth === 0) {
                // Only split on commas at depth 0
                if (current.trim()) {
                    result.push(current.trim());
                }
                current = '';
            } else {
                current += char;
            }
        }

        // Add the last segment
        if (current.trim()) {
            result.push(current.trim());
        }

        return result;
    }
}

export const  functionParser : FunctionParser =new  FunctionParser();