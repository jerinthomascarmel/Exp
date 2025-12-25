
import { Importer } from "export-ts"
import  type { StdioParameters } from "export-ts";

const main =async ()=>{

  const params : StdioParameters ={
    command: "node",
    args: ["./dist/server.js"]
  }

  const importer = new Importer(params); 
  await importer.connect();
  const greeting = importer.getFunction("greeting");
  const result = await greeting({name:"jerin" , age: 22} )
  console.log(result)
  console.log(typeof result)
  importer.close();
  
}


main();

// const greeting = importer.getFunction("greeting");
// const result = await greeting({name:"poori"});

// Steps to do ! 
// 1. solve the argments schema and return type schema for the function 
// 2. solve the getFunction method to return a callable function with proper types
// 3. get all the arguments if available and return type for the function
