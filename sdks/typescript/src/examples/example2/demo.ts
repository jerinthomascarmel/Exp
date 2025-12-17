import { zodToJsonSchema } from "zod-to-json-schema";
import { jsonSchemaToZod } from "json-schema-to-zod";
import { z } from "zod";

const zSchema = z.object({name:z.any()});
const zSchema2 =z.array(z.number());

const zshema3 = z.any()


const jsonSchema = zodToJsonSchema(zshema3);
console.log("JSON Schema:", jsonSchema);

console.log(JSON.stringify(jsonSchema));

// const zodCode = jsonSchemaToZod(jsonSchema as any,{ module: "cjs" });
// const zSchemaV2 = eval(zodCode) as z.ZodTypeAny;
// const parseResult = zSchemaV2.safeParse([1, "2", { a: 3 }]);
// console.log(parseResult);
