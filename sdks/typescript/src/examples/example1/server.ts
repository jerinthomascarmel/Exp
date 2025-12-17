import { StdioExporterTransport } from "../../exporter/stdio.js";
import { Exporter } from "../../exporter/index.js";
import { z } from 'zod';

const transport = new StdioExporterTransport(); 
const exporter = new Exporter(); 

// const greeting = ( {name } : { name :string} )=>{
//     return `hello ${name}`
// }
    

function greeting(name:string,age:number){
    return name+age;
}


// exporter.registerFunction("greeting" , {
//     description:"this function greets", 
// }, greeting);

// or 

// exporter.export("greeting", greeting);

exporter.connect(transport); 
// or 
// exporter.expose();

