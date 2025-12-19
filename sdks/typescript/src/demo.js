

import { functionParser } from "../dist/validation/utils.js"

function hello({a ,  d : [a , b]}){
    return "hello"
}


function hello2(obj){
    return "hello2"
}

let jsonSchema = functionParser.parseFunctionJsonSchema(hello2);
console.log(JSON.stringify(jsonSchema));
