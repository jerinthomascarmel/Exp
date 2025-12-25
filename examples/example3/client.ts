
import { Importer } from "export-ts"
import type { StdioParameters } from "export-ts";

const main =async ()=>{
  const params : StdioParameters=  {
    command: "uv",
    args: ["run","./server.py"]
  }

  const importer = new Importer(params); 
  await importer.connect();
  const add = importer.getFunction("add");
  const result = await add({a:10 , b:20});
  console.log("Result of add function: " , result);
  importer.close();
}


main();

// const greeting = importer.getFunction("greeting");
// const result = await greeting({name:"poori"});

// Steps to do ! 
// 1. solve the argments schema and return type schema for the function 
// 2. solve the getFunction method to return a callable function with proper types
// 3. get all the arguments if available and return type for the function
