import { createContext } from "react";

const BatteryContext = createContext({
    batteries: [],
    setBaterries: (a) => { },
    old: false,
    setOld: (a) => { }
});

export default BatteryContext;