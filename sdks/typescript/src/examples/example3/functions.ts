// import FunctionParser from "../validation/utils";

interface User {
    name : string; 
    age : number ;
}

function greetings({name , age} : User): string {
    return `Hello, my name is ${name} and I am ${age} years old.`;
}

const comp  : (name : string , age?: number )=> User = (name : string ="jt" , age?: number ) => {
    return  { name : "jserin " , age : 54}
}

type AreaParams = Parameters<typeof greetings>;

// let fp  = new FunctionParser();
// fp.parseFunctionParams(greetings)