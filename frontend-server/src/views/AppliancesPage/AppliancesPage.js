import axios from 'axios';
import { useEffect, useState } from 'react';
import { Accordion, Container } from 'react-bootstrap';
import Category from './Category';
import DataContext from './DataContext';

function AppliancesPage() {
    const [categories, setCategories] = useState([]);
    const [appliances, setAppliances] = useState([]);
    const [tasks, setTasks] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [old, setOld] = useState();

    useEffect(() => {
        const url = 'http://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_SMART_HUB_PORT
        axios(url + '/appliances', {
            method: 'get'
        }).then(response => {
            const appliances = response.data;
            const set = new Set();
            for (const a of appliances) {
                set.add(a.category)
            }
            setCategories(Array.from(set));
            setAppliances(response.data);

            axios(url + '/programs', {
                method: 'get'
            }).then(response => {
                setPrograms(response.data);

                axios(url + '/tasks', {
                    method: 'get'
                }).then(response => {
                    setTasks(response.data);
                });
            });
        });
    }, [old]);

    return (
        <Container fluid style={{ marginTop: '20px' }}>
            <DataContext.Provider value={{ appliances, setAppliances, tasks, setTasks, programs, setPrograms, old, setOld }}>
                <Accordion flush>
                    {
                        categories && categories.map(c => {
                            return <Accordion.Item key={c} eventKey={c}>
                                <Accordion.Header>{c}</Accordion.Header>
                                <Accordion.Body><Category name={c} /></Accordion.Body>
                            </Accordion.Item>
                        })
                    }
                </Accordion>
            </DataContext.Provider>
        </Container>
    );
}

export default AppliancesPage;
