
import { Exporter } from "export-ts"

const main = async ()=>{
    const exporter = new Exporter(); 
 
    const fn = function add({a , b  }: {a:number , b:number}): number {
        return a+b;
    }
    
    exporter.export(fn);
    await exporter.connect(); 
}

main()


