import axios from "axios";
import React, { useContext } from "react";
import { ListGroup } from 'react-bootstrap';
import Button from "react-bootstrap/esm/Button";
import { FaUnlink, FaLink } from 'react-icons/fa';
import BatteryContext from "./BatteryContext";
import DetailRow from "../DetailRow";

const Battery = (props) => {
    let battery = props.battery;
    let state = battery.currentRate > 0 ? "Charging " : "Discharging ";
    let connected = battery.connected;
    const { old, setOld } = useContext(BatteryContext);

    const tokWh = (num) => {
        return parseFloat(num / (3600 * 1000)).toFixed(3)
    }

    const changeState = () => {
        let url = encodeURI('http://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_SMART_HUB_PORT + '/batteries/' + battery.name + "/" + (connected ? "disconnect" : "connect"));

        axios.post(url).then(response => {
            setOld(!old);
        });
    }

    return (
        battery &&
        <ListGroup.Item>
            <div style={{ display: 'flex', flexDirection: "row" }}>
                <div style={{ display: 'flex', flexDirection: "column", justifyContent: 'space-between', align: 'left', width: '100%' }}>
                    <DetailRow info={<p style={{ fontWeight: 'bold', marginBottom: '15px' }}>{battery.name}</p>} value={(connected ? state + (parseFloat(battery.currentRate / 1000).toFixed(3)) + "kW" : "Disconnected")} />
                    <DetailRow info="Model" value={battery.model} />
                    <DetailRow info="Capacity" value={tokWh(battery.currentCapacity) + "/" + tokWh(battery.maxCapacity) + " kWh"} />
                </div>
                <div style={{ display: 'flex', flexDirection: "column", justifyContent: 'space-evenly', marginLeft: '25px', align: 'right' }}>
                    <Button variant="outline-info" style={{ display: 'flex', alignItems: 'center' }} onClick={changeState}>
                        {connected ? <FaUnlink /> : <FaLink />}
                    </Button>
                </div>
            </div>
        </ListGroup.Item>
    );
}

export default Battery;