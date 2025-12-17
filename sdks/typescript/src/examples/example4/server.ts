import { StdioExporterTransport } from "../../exporter/stdio.js";
import { Exporter } from "../../exporter/index.js";


const main = async ()=>{
    const transport = new StdioExporterTransport(); 
    const exporter = new Exporter(); 
    
    const fn = function greeting(name:string,age:number){
        return name+age;
    }
    exporter.export(fn);
    
    await exporter.connect(transport); 
    // or 
    // exporter.expose();
}

main()


