import axios from "axios";
import React, { useContext, useEffect } from "react";
import Button from "react-bootstrap/esm/Button";
import { FaClock, FaPlay } from 'react-icons/fa';
import DataContext from "./DataContext";
import DetailRow from "../DetailRow";

const Program = (props) => {
    let applianceId = props.applianceId;
    let applianceName = props.applianceName;
    let programName = props.programName;
    const { programs, appliances, old, setOld } = useContext(DataContext);
    const [program, setProgram] = React.useState();
    const [inactive, setInactive] = React.useState();

    const toHHMMSS = function (num) {
        var hours = Math.floor(num / 3600);
        var minutes = Math.floor((num - (hours * 3600)) / 60);
        var seconds = num - (hours * 3600) - (minutes * 60);

        if (hours < 10) { hours = "0" + hours; }
        if (minutes < 10) { minutes = "0" + minutes; }
        if (seconds < 10) { seconds = "0" + seconds; }
        return hours + ':' + minutes + ':' + seconds;
    }

    const getPriorityString = function (p) {
        switch (p) {
            case 1:
                return "Very low";
            case 2:
                return "Low";
            case 3:
                return "Medium";
            case 4:
                return "High";
            case 5:
                return "Very high";
            default:
                return "User only";
        }
    }

    const startTask = () => {
        let url = encodeURI('http://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_SMART_HUB_PORT + '/appliances/' + applianceName + "/tasks/start");
        axios.post(url, {
            'programName': programName
        }).then(
            response => {
                setOld(!old)
            }
        );
    };

    const programTask = () => {
        let url = encodeURI('http://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_SMART_HUB_PORT + '/appliances/' + applianceName + "/tasks/program");
        axios.post(url, {
            'programName': programName
        }).then(response => {
            setOld(!old)
        });
    };

    useEffect(() => {
        for (const p of programs) {
            if (p.name == programName && p.applianceId == applianceId) {
                setProgram(p);
                break;
            }
        }
    }, [programName, programs]);

    useEffect(() => {
        for (const a of appliances) {
            if (a._id === applianceId) {
                if (a.currentTask == null)
                    setInactive(false);
                else
                    setInactive(true);
                break;
            }
        }
    }, [applianceId, appliances]);

    return (
        program &&
        <div style={{ display: 'flex', flexDirection: "row" }}>
            <div style={{ display: 'flex', flexDirection: "column", justifyContent: 'space-between', align: 'left', width: '100%' }}>
                <DetailRow info={<p style={{ fontWeight: 'bold', marginBottom: '15px' }}>{program.name}</p>} value={(program.averagePower + " W " + (program.generatesPower ? "production" : "consumption") + " (avg.)")} />
                <DetailRow info="Duration (avg.)" value={program.duration == -1 ? "Indefinite" : toHHMMSS(program.duration)} />
                <DetailRow info="Priority" value={getPriorityString(program.priority)} />
                <DetailRow info="Downgradeable" value={program.downgradeable ? "True" : "False"} />
                <DetailRow info="Interruptible" value={program.interruptible ? "True" : "False"} />
                <DetailRow info="Programmable" value={program.programmable ? "True" : "False"} />
            </div>
            <div style={{ display: 'flex', flexDirection: "column", justifyContent: 'space-evenly', marginLeft: '25px', align: 'right' }}>
                <Button disabled={inactive} variant="outline-info" style={{ display: 'flex', alignItems: 'center' }} onClick={inactive ? null : startTask}>
                    <FaPlay />
                </Button>
                <Button disabled={program.programmable ? false : true} variant="outline-info" style={{ display: 'flex', alignItems: 'center' }} onClick={programTask}>
                    <FaClock />
                </Button>
            </div>
        </div>

    );
}

export default Program;