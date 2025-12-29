import { Exporter } from "export-ts";

const exp= new Exporter();

(async ()=>{
    class CustomClass{
        name: string; 
        just : string; 
        constructor(name: string){
            this.name = name;
            this.just = "pari";
        }
        greeting(){}
    }

    function greet({name } : {name: string}): CustomClass{
        return new CustomClass(name);
    }

    exp.export(greet);
    await exp.connect(); 
})();

