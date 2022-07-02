import { useContext } from "react";

import { Accordion } from 'react-bootstrap';
import Appliance from "./Appliance";
import DataContext from './DataContext';

const Category = (props) => {
    const { appliances } = useContext(DataContext)
    const appliancesByCat = [];
    for (const a of appliances) {
        if (a.category === props.name)
            appliancesByCat.push(a)
    }

    return (
        <Accordion flush>
            {
                appliancesByCat && appliancesByCat.map(a => {
                    return <Accordion.Item key={a.name} eventKey={a.name}>
                        <Accordion.Header>{a.name}</Accordion.Header>
                        <Accordion.Body><Appliance key={a.name} appliance={a} /></Accordion.Body>
                    </Accordion.Item>
                })
            }
        </Accordion>
    );
}

export default Category;