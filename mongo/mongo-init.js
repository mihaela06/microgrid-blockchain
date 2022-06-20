db.createUser({
    user: 'root',
    pwd: 'password',
    roles: [
        {
            role: 'dbOwner',
            db: 'hub',
        },
    ],
});