

import { functionParser } from "../dist/validation/utils.js"

import { zodToJsonSchema } from "zod-to-json-schema";

import { z } from "zod";

const zSchema = z.object({ name : z.any() , age:z.object({ name : z.string()}) , price : z.any()});

const jsonSchema = zodToJsonSchema(zSchema);
console.log(JSON.stringify(jsonSchema));
console.log('\n');

// const zodCode = jsonSchemaToZod(jsonSchema as any,{ module: "cjs" });
// const zSchemaV2 = eval(zodCode) as z.ZodTypeAny;
// const parseResult = zSchemaV2.safeParse([1, "2", { a: 3 }]);
// console.log(parseResult);


// function hello({name: { age , superval : { jerin } } , address }){
//     return "hello"
// }

function hello({name , age }){
    return "hello"
}

console.log(hello({name : "jerin" , age: "pari" }))


let jsonSchema2 = functionParser._parseFunctionInputSchema(hello);
console.log(JSON.stringify(jsonSchema2));
