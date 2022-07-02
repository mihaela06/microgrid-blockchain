import React from "react";

import { ListGroup, Accordion } from 'react-bootstrap';
import DetailRow from "../DetailRow";
import Program from "./Program"
import Task from "./Task";


const Appliance = (props) => {
    let appliance = props.appliance;

    return (
        <div>
            <ListGroup variant="flush">
                <ListGroup.Item key="Model"><DetailRow info="Model" value={appliance.model} /></ListGroup.Item>
                <ListGroup.Item key="Current task"><DetailRow info="Current task" value={appliance.currentTask} /></ListGroup.Item>
                <ListGroup.Item key="Programs">
                    <Accordion flush>
                        <Accordion.Item key={appliance.name} eventKey={appliance.name}>
                            <Accordion.Header>Programs</Accordion.Header>
                            <Accordion.Body>
                                <ListGroup variant="flush">
                                    {
                                        appliance.programs.map(p => {
                                            return <ListGroup.Item key={p}>
                                                <Program applianceName={appliance.name}
                                                    applianceId={appliance._id}
                                                    programName={p} />
                                            </ListGroup.Item>
                                        })
                                    }
                                </ListGroup>
                            </Accordion.Body>
                        </Accordion.Item>
                    </Accordion>
                </ListGroup.Item>
                <ListGroup.Item key="Tasks">
                    <Accordion flush>
                        <Accordion.Item key={appliance.name} eventKey={appliance.name}>
                            <Accordion.Header>Tasks</Accordion.Header>
                            <Accordion.Body>
                                <ListGroup variant="flush">
                                    {
                                        appliance.tasks.map(t => {
                                            return (
                                                <Task applianceName={appliance.name}
                                                    applianceId={appliance._id}
                                                    taskId={t}
                                                    key={t} />
                                            )
                                        })
                                    }
                                </ListGroup>
                            </Accordion.Body>
                        </Accordion.Item>
                    </Accordion>
                </ListGroup.Item>
            </ListGroup>
        </div >
    );
}

export default Appliance;