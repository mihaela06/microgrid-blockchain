import { createContext } from "react";

const DataContext = createContext({
    appliances: [],
    setAppliances: (a) => { },
    tasks: [],
    setTasks: (a) => { },
    programs: [],
    setPrograms: (a) => { },
    old: false,
    setOld: (a) => {}
});

export default DataContext;