import { Link, Route, Routes } from 'react-router-dom';

import './App.css';

import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';

import AppliancesPage from './views/AppliancesPage/AppliancesPage';
import BatteriesPage from './views/BatteriesPage/BatteriesPage';
import { GraphPage } from './views/GraphPage/GraphPage';


const App = () => (
  <div>
    <Navbar bg="dark" variant="dark">
      <Container>
        <Navbar.Brand as={Link} to="/">Smart Hub</Navbar.Brand>
        <Nav className="justify-content-end">
          <Nav.Link as={Link} to="/">Home</Nav.Link>
          <Nav.Link as={Link} to="/appliances">Appliances</Nav.Link>
          <Nav.Link as={Link} to="/batteries">Batteries</Nav.Link>
        </Nav>
      </Container>
    </Navbar>
    <Container>
      <Routes>
        <Route path='/' element={<GraphPage />} />
        <Route path='/appliances' element={<AppliancesPage />} />
        <Route path='/batteries' element={<BatteriesPage />} />
      </Routes>
    </Container>
  </div>
);

export default App;
