import React from "react";

class DetailRow extends React.Component {
    render() {
        let props = this.props;
        let info = props.info;
        let value = props.value;
        return (
            <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between' }}>
                <div style={{ align: 'left', marginRight: '10px' }}>{info}</div>
                <div style={{ align: 'right' }}>{value ? value : "None"}</div>
            </div >
        );
    }
}

export default DetailRow;