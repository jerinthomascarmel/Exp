import { StdioImporterTransport } from "../../importer/stdio.js";
import { Importer } from "../../importer/index.js"


const main =async ()=>{

  const transport = new StdioImporterTransport({
      command: "node",
      args: ["./dist/examples/example4/server.js"]
    });

  const importer = new Importer(); 
  await importer.import(transport);

  const result = await importer.callFunction({name:"greeting", arguments:{name:"jerin" , age: 22} })
  console.log(result)
  console.log(typeof result)
  transport.close();
  
}


main();

// const greeting = importer.getFunction("greeting");
// const result = await greeting({name:"poori"});

// Steps to do ! 
// 1. solve the argments schema and return type schema for the function 
// 2. solve the getFunction method to return a callable function with proper types
// 3. get all the arguments if available and return type for the function
