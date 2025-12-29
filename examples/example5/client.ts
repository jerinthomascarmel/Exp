
import { Importer } from "export-ts"
import  type { StdioParameters } from "export-ts";

(async ()=>{
  const params : StdioParameters ={
    command: "node",
    args: ["./dist/server.js"]
  }

  const importer = new Importer(params); 
  await importer.connect();
  let lists = await importer.listFunctions();
  console.log("Available functions:", JSON.stringify(lists));
  const greet = importer.getFunction("greet"); 
  const res = await greet({name: "Alice"});
  console.log("Response from greet:", res);
  importer.close();
})();

