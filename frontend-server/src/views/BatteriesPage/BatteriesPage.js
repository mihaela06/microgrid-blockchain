import axios from 'axios';
import { useEffect, useState } from 'react';
import { Container } from 'react-bootstrap';
import BatteryContext from './BatteryContext'
import { ListGroup } from 'react-bootstrap';
import Battery from './Battery';

function BatteriesPage() {
    const [batteries, setBatteries] = useState([]);
    const [old, setOld] = useState();

    useEffect(() => {
        const url = 'http://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_SMART_HUB_PORT
        axios(url + '/batteries', {
            method: 'get'
        }).then(response => {
            setBatteries(response.data);
        });
    }, [old]);

    return (
        <Container fluid style={{ marginTop: '20px' }}>
            <BatteryContext.Provider value={{ batteries, setBatteries, old, setOld }}>
                <ListGroup variant="flush">
                    {
                        batteries && batteries.map(b => {
                            return (
                                <Battery battery={b}
                                    key={b._id} />
                            )
                        })
                    }
                </ListGroup>
            </BatteryContext.Provider>
        </Container>
    );
}

export default BatteriesPage;
