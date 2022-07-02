import axios from "axios";
import { useEffect, useState } from 'react';
import { Form } from "react-bootstrap";
import moment from "moment";
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Label } from 'recharts';

export const GraphPage = () => {
    const FREQ = 10;
    const socketUrlDR = 'ws://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_DATA_STREAM_PORT + '/dr';
    const socketUrlED = 'ws://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_DATA_STREAM_PORT + '/ed';
    const [energyData, setEnergyData] = useState([]);
    const [interval, setInterval] = useState(1800);
    const [partialEnergyData, setPartialEnergyData] = useState([])
    const [selected, setSelected] = useState("Total");
    const [applianceNames, setApplianceNames] = useState({});
    const [viewDR, setViewDR] = useState(true);
    const [minY, setMinY] = useState(-2000);
    const [maxY, setMaxY] = useState(2000);
    const [DRSignal, setDRSignal] = useState([]);

    const DRLen = 12;   // 2 min

    const socketDR = useWebSocket(socketUrlDR);
    const lastMessageDR = socketDR.lastMessage;

    const socketED = useWebSocket(socketUrlED);
    const lastMessageED = socketED.lastMessage;

    const intervalToString = (i) => {
        if (i < 3600) {
            return (i / 60 + " min".padEnd(5));
        }
        return (i / 3600 + " h  ").padEnd(5);
    }

    const timestampToString = (t) => {
        // returns string in UTC+3
        let date = new Date(t * 1000 + 3600 * 3);
        return date.toISOString().split('.')[0];
    }

    const stringToTimestamp = (s) => {
        let v = (new Date(s)).getTime() / 1000;
        return Math.floor(v + 3600 * 3);
    }


    useEffect(() => {
        const url = 'http://' + process.env.REACT_APP_HOST_IP + ':' + process.env.REACT_APP_SMART_HUB_PORT
        axios(url + '/appliances', {
            method: 'get'
        }).then(response => {
            const app = response.data;
            let an = {};
            for (const a of app) {
                an[a._id] = a.name;
            }
            setApplianceNames(an);

            axios(url + '/data/values', {
                method: 'get'
            }).then(response => {
                const values = response.data;
                let data = []
                let latestTs = stringToTimestamp(values[0].ts)
                let oldestTs = stringToTimestamp(values[values.length - 1].ts)
                for (var i = DRLen; i >= 1; i--) {
                    let obj = {};
                    obj['Timestamp'] = latestTs + i * FREQ;
                    obj['Total'] = null;
                    obj['DR Signal'] = null;
                    obj['Current DR Signal'] = null;
                    for (const a in an) {
                        obj[an[a]] = null;
                    }
                    data.push(obj);
                }
                for (const v of values) {
                    let obj = {};
                    obj['Timestamp'] = stringToTimestamp(v.ts);
                    obj['Total'] = v.total;
                    obj['DR Signal'] = v.current_dr;
                    obj['Current DR Signal'] = null;
                    for (const a in v.appliances) {
                        obj[an[a]] = v.appliances[a]
                    }
                    for (const a in an) {
                        if (!(a in v.appliances))
                            obj[an[a]] = null;
                    }
                    data.push(obj);
                }
                let lenToComplete = (24 * 3600 - (latestTs - oldestTs)) / FREQ;
                for (var i = 1; i < lenToComplete; i++) {
                    let obj = {};
                    obj['Timestamp'] = oldestTs - i * FREQ;
                    obj['Total'] = null;
                    obj['DR Signal'] = null;
                    obj['Current DR Signal'] = null;
                    for (const a in an) {
                        obj[an[a]] = null;
                    }
                    data.push(obj);
                }
                setEnergyData(data.reverse());
                let minSelected = Math.min(...(data.map(a => a[selected] ? a[selected] : Number.MAX_SAFE_INTEGER)));
                let maxSelected = Math.max(...(data.map(a => a[selected] ? a[selected] : Number.MIN_SAFE_INTEGER)));
                let minOldDR = Math.min(...(data.map(a => a['DR Signal'] ? a['DR Signal'] : Number.MAX_SAFE_INTEGER)));
                let maxOldDR = Math.max(...(data.map(a => a['DR Signal'] ? a['DR Signal'] : Number.MIN_SAFE_INTEGER)));
                setMinY(Math.floor(Math.min(minSelected, minOldDR)));
                setMaxY(Math.ceil(Math.max(maxSelected, maxOldDR)));
            });
        });

    }, []);

    useEffect(() => {
        if (lastMessageDR !== null && energyData) {
            console.log(lastMessageDR)
            let s = JSON.parse(lastMessageDR.data.split(":")[1]);
            console.log(s)
            if (s.length > 1)
                setDRSignal(s);
            else
                setDRSignal([]);
            setMinY(Math.floor(Math.min(minY, ...s)));
            setMaxY(Math.ceil(Math.max(maxY, ...s)));
        }
    }, [lastMessageDR]);

    useEffect(() => {
        if (lastMessageED != null && energyData.length > 0) {
            console.log(energyData.length)
            let newData = [...energyData.slice(0, -DRLen)];
            let newED = JSON.parse(lastMessageED.data);
            console.log(newData.length)
            let newObj = {};
            newObj['Total'] = newED.total;
            newObj['DR Signal'] = newED.current_dr;
            newObj['Current DR Signal'] = null;
            var latestTs = stringToTimestamp(newED.ts);
            newObj['Timestamp'] = latestTs;
            for (const a in newED.appliances) {
                newObj[applianceNames[a]] = newED.appliances[a]
            }
            newData.push(newObj);
            for (var i = 1; i <= DRLen; i++) {
                let obj = {};
                obj['Total'] = null;
                obj['DRSignal'] = null;
                obj['Current DR Signal'] = (DRSignal.length >= i) ? DRSignal[i - 1] : null;
                obj['Timestamp'] = latestTs + FREQ * i;
                newData.push(obj);
            }
            setMaxY(Math.ceil(Math.max(maxY, newED.total, newED.current_dr)));
            setMinY(Math.floor(Math.min(minY, newED.total, newED.current_dr)));
            newData.shift();
            setEnergyData(newData);
        }
    }, [lastMessageED]);

    useEffect(() => {
        if (energyData.length > 0) {
            let window = [];
            let acceptOver = energyData[energyData.length - 1]['Timestamp'] - interval;

            for (const e of energyData) {
                if (e['Timestamp'] >= acceptOver)
                    window.push(e)
            }
            setPartialEnergyData(window);
            console.log(window.slice(-20));
        }
    }, [interval, setInterval, energyData, setEnergyData])

    useEffect(() => {
        if (selected === "Total")
            setViewDR(true);
        else
            setViewDR(false);
    }, [selected, setSelected])

    const DataFormatter = (number) => {
        if (number > 1000) {
            return (Math.floor(number) / 1000).toString() + ' kW';
        } else {
            return Math.floor(number).toString() + ' W';
        }
    }

    return (
        <div>
            <div style={{ display: 'flex', flexDirection: "row", justifyContent: 'space-evenly', marginTop: '30px' }}>
                <div style={{ width: 'fit-content', margin: '10px', align: 'right' }}>
                    <Form.Select onChange={(e) => setInterval(e.target.value)}>
                        <option value="1800">{intervalToString(1800)}</option>
                        <option value="3600">{intervalToString(3600)}</option>
                        <option value="21600">{intervalToString(6 * 3600)}</option>
                        <option value="43200">{intervalToString(12 * 3600)}</option>
                        <option value="86400">{intervalToString(24 * 3600)}</option>
                    </Form.Select>
                </div>
                <div style={{ width: 'fit-content', margin: '10px', align: 'right' }}>
                    <Form.Select onChange={(e) => setSelected(e.target.value)}>
                        <option value="Total">Total</option>
                        {applianceNames && Object.keys(applianceNames).map((a, i) => {
                            return <option value={applianceNames[a]} key={i}>{applianceNames[a]}</option>
                        })}
                    </Form.Select>
                </div>
            </div>
            <div style={{ marginTop: "20px" }}>
                {partialEnergyData &&
                    <ResponsiveContainer width={"100%"} height={600}>
                        <LineChart
                            data={partialEnergyData}
                            margin={{ top: 50, right: 50, left: 50, bottom: 50 }}
                        >
                            <XAxis dataKey="Timestamp"
                                tickFormatter={timeStr => moment(timeStr * 1000).format('HH:mm')}
                            >
                                <Label
                                    style={{
                                        textAnchor: "middle",
                                        fontSize: "130%",
                                        fill: "black",
                                    }}
                                    dy={40}
                                    value={"Time"} />
                            </XAxis>
                            <YAxis tickCount={11} tickFormatter={DataFormatter} type="number" domain={[Math.floor(minY), Math.ceil(maxY)]} allowDecimals={false}>
                                <Label
                                    style={{
                                        textAnchor: "middle",
                                        fontSize: "130%",
                                        fill: "black",
                                    }}
                                    angle={270}
                                    dx={-50}
                                    value={"Power consumption"} />
                            </YAxis>
                            <Tooltip
                                formatter={(value, name, props) => [DataFormatter(value), name]}
                                labelFormatter={(value) => moment(value * 1000).format('HH:mm:ss')}
                            />
                            <Line type="monotone" strokeWidth={3} isAnimationActive={false} dataKey={selected} stroke="#000000" yAxisId={0} name={selected} dot={false} />
                            {viewDR && <Line type="monotone" strokeWidth={3} isAnimationActive={false} dataKey={'Current DR Signal'} stroke="#ff0000" yAxisId={0} name="DR Signal" dot={false} />}
                            {viewDR && <Line type="monotone" strokeWidth={3} isAnimationActive={false} dataKey={'DR Signal'} stroke="#00aa00" yAxisId={0} name={"Past DR Signal"} dot={false} />}
                        </LineChart>
                    </ResponsiveContainer>}
            </div>
        </div>
    );
};
