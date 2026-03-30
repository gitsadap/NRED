<?php
$pg_host = getenv("DB_HOST") ?: "aws-1-ap-northeast-1.pooler.supabase.com";
$pg_user = "agi";
$pg_pass = "adminagi";
$pg_db   = "nred";

try {
    $dsn = "pgsql:host=$pg_host;dbname=$pg_db";
    $pdo = new PDO($dsn, $pg_user, $pg_pass);
    
    $stmt = $pdo->query("SELECT count(*) FROM api.faculty");
    $count = $stmt->fetchColumn();
    
    echo "Rows in api.faculty: $count\n";
    
    if ($count > 0) {
        $stmt = $pdo->query("SELECT fname, fname_en FROM api.faculty LIMIT 3");
        print_r($stmt->fetchAll(PDO::FETCH_ASSOC));
    }

} catch (PDOException $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>
