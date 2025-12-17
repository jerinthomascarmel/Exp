
import { Exporter } from "export-ts"


const main = async ()=>{
    const exporter = new Exporter(); 
    const fn = function greeting(name:string,age:number){
        return name+age;
    }
    exporter.export(fn);
    await exporter.connect(); 
}

main()


