<?php
// sync_faculty.php
// Syncs faculty data from MySQL to PostgreSQL

header('Content-Type: text/plain');

// --- Configuration ---
// MySQL (Source)
$mysql_host = "10.10.58.16";
$mysql_user = "gitsadap";
$mysql_pass = "it[[{ko-hv,^]8ItgdK9i";
$mysql_db   = "db_user";

// PostgreSQL (Destination)
$pg_host = getenv("DB_HOST") ?: "aws-1-ap-northeast-1.pooler.supabase.com";
$pg_user = "agi";
$pg_pass = "adminagi";
$pg_db   = "nred";

try {
    // 1. Connect to MySQL (Source)
    $mysql_dsn = "mysql:host=$mysql_host;dbname=$mysql_db;charset=tis620";
    $mysql_pdo = new PDO($mysql_dsn, $mysql_user, $mysql_pass);
    $mysql_pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    // $mysql_pdo->exec("SET NAMES 'tis620'"); // Optional if charset in DSN works

    // 2. Connect to PostgreSQL (Destination)
    $pg_dsn = "pgsql:host=$pg_host;dbname=$pg_db";
    $pg_pdo = new PDO($pg_dsn, $pg_user, $pg_pass);
    $pg_pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    // Load Manual English Names if available
    $manual_en_names = [];
    if (file_exists('faculty_en.json')) {
        $json_data = file_get_contents('faculty_en.json');
        $en_list = json_decode($json_data, true);
        foreach ($en_list as $item) {
            $manual_en_names[$item['id']] = $item['name_en'];
        }
    }
    
    // Ensure schema exists
    $pg_pdo->exec(file_get_contents('schema.sql'));

    echo "Connected to both databases.\n";

    // 3. Fetch Data from MySQL
    // Note: Removed u.expertise because it does not exist in the table `user`
    $sql = "SELECT 
                u.user_id, 
                u.fname, u.lname, 
                u.fname_eng, u.lname_eng, 
                u.email, u.profile_image, 
                p.prefix_name AS prefix, 
                ap.th_name AS acad_pos,
                ap.en_name AS acad_pos_en,
                pos.position_name AS admin_pos
            FROM user u
            LEFT JOIN prefix p ON u.prefix_id = p.prefix_id
            LEFT JOIN academic_position ap ON u.acad_pos_id = ap.acad_pos_id
            LEFT JOIN position pos ON u.position_id = pos.position_id
            WHERE u.depart_id = 4";
    
    $stmt = $mysql_pdo->query($sql);
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    echo "Fetched " . count($rows) . " rows from MySQL.\n";

    // 4. Sync to PostgreSQL
    // Removed expertise from INSERT/UPDATE
    $insert_sql = "INSERT INTO api.faculty (
        id, prefix, fname, lname, fname_en, lname_en, 
        position, position_en, admin_position, 
        email, image, updated_at
    ) VALUES (
        :id, :prefix, :fname, :lname, :fname_en, :lname_en, 
        :position, :position_en, :admin_position, 
        :email, :image, NOW()
    ) ON CONFLICT (id) DO UPDATE SET
        prefix = EXCLUDED.prefix,
        fname = EXCLUDED.fname,
        lname = EXCLUDED.lname,
        fname_en = EXCLUDED.fname_en,
        lname_en = EXCLUDED.lname_en,
        position = EXCLUDED.position,
        position_en = EXCLUDED.position_en,
        admin_position = EXCLUDED.admin_position,
        email = EXCLUDED.email,
        image = EXCLUDED.image,
        updated_at = NOW();";
    
    $pg_stmt = $pg_pdo->prepare($insert_sql);

    foreach ($rows as $row) {
        $uid = $row['user_id'];
        
        // Convert TIS-620 to UTF-8 for PostgreSQL
        array_walk($row, function(&$value, $key) {
            if (is_string($value)) {
                $value = iconv('TIS-620', 'UTF-8', $value); 
            }
        });

        // Determine English Name
        $fname_en = trim($row['fname_eng'] ?? '');
        $lname_en = trim($row['lname_eng'] ?? '');
        $full_en_name_manual = $manual_en_names[$uid] ?? '';
        
        // If manual name exists, we might want to split it or store it.
        // Our table has fname_en/lname_en. 
        // If the manual name is "Dr. John Doe", checking it is hard.
        // For simplicity, if database EN name is missing, but manual exists, 
        // we might just put the whole manual name in fname_en and leave lname_en empty?
        // OR try to parse it. 
        // "Dr. Pantip Klomjek" -> prefix=Dr., fname=Pantip, lname=Klomjek.
        
        if (empty($fname_en) && !empty($full_en_name_manual)) {
            // Very basic parse
            $parts = explode(' ', $full_en_name_manual);
            // remove Dr. if present
            if ($parts[0] == 'Dr.' || $parts[0] == 'Mr.' || $parts[0] == 'Ms.') {
                array_shift($parts);
            }
            $lname_en = array_pop($parts);
            $fname_en = implode(' ', $parts);
        }

        // Map fields
        $params = [
            ':id' => $row['user_id'],
            ':prefix' => $row['prefix'],
            ':fname' => $row['fname'],
            ':lname' => $row['lname'],
            ':fname_en' => $fname_en,
            ':lname_en' => $lname_en,
            ':position' => $row['acad_pos'],
            ':position_en' => $row['acad_pos_en'],
            ':admin_position' => $row['admin_pos'],
            ':email' => $row['email'],
            ':image' => $row['profile_image']
        ];
        
        $pg_stmt->execute($params);
    }
    
    echo "Sync completed successfully.\n";

} catch (PDOException $e) {
    die("Database Error: " . $e->getMessage() . "\n");
}
?>
