import axios from "axios";
import React, { useContext, useEffect } from "react";
import { ListGroup } from 'react-bootstrap';
import Button from "react-bootstrap/esm/Button";
import { FaBan, FaForward, FaPause } from 'react-icons/fa';
import DataContext from "./DataContext";
import DetailRow from "../DetailRow";

const Task = (props) => {
    let applianceName = props.applianceName;
    let taskId = props.taskId;
    const [task, setTask] = React.useState();

    const { tasks, old, setOld } = useContext(DataContext);

    const getStateString = function (s) {
        switch (s) {
            case 1:
                return "Pending";
            case 2:
                return "In progress";
            case 3:
                return "Paused";
            case 5:
                return "Finished";
            default:
                return "Canceled";
        }
    }

    useEffect(() => {
        for (const t of tasks) {
            if (t._id == taskId) {
                setTask(t);
                break;
            }
        }
    }, [taskId, tasks]);

    const taskAction = () => {
        switch (task.state) {
            case 2:
                // "In progress";
                modifyTask("pause");
                break;
            case 3:
                // "Paused"
                modifyTask("resume");
                return <FaForward />
            default:
                return null;
        }
    }

    const modifyTask = (newState) => {
        let url = encodeURI('http://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_SMART_HUB_PORT + '/appliances/' + applianceName + "/tasks/" + newState);
        axios.post(url).then(response => {
            setOld(!old);
        });
    };

    const cancelTask = () => {
        let url = encodeURI('http://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_SMART_HUB_PORT + '/appliances/' + applianceName + "/tasks/" + task._id);
        axios.delete(url).then(response => {
            setOld(!old);
        });
    };

    const getIcon = () => {
        switch (task.state) {
            case 1:
                // "Pending";
                return null;
            case 2:
                // "In progress";
                return <FaPause />
            case 3:
                // "Paused";
                return <FaForward />
            default:
                return null;
        }
    }

    const getButton = () => {
        if (task.state === 2 || task.state === 3)
            return true;
        return false;
    }

    if (task && task.state > 3)
        return null;

    return (
        task &&
        <ListGroup.Item key={taskId}>
            <div style={{ display: 'flex', flexDirection: "row" }}>
                <div style={{ display: 'flex', flexDirection: "column", justifyContent: 'space-between', align: 'left', width: '100%' }}>
                    <DetailRow info={<p style={{ fontWeight: 'bold', marginBottom: '15px' }}>ID</p>} value={(task._id)} />
                    <DetailRow info="Program" value={task.programName} />
                    <DetailRow info="State" value={getStateString(task.state)} />
                </div>
                <div style={{ display: 'flex', flexDirection: "column", justifyContent: 'space-evenly', marginLeft: '25px', align: 'right' }}>
                    {getButton() && <Button variant="outline-info" style={{ display: 'flex', alignItems: 'center' }} onClick={taskAction}>
                        {getIcon()}
                    </Button>}
                    <Button variant="outline-info" style={{ display: 'flex', alignItems: 'center' }} onClick={cancelTask} >
                        <FaBan />
                    </Button>
                </div>
            </div>
        </ListGroup.Item>
    );
}

export default Task;