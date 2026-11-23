flowchart TB
    subgraph VMware ["Entorno Virtual Base (VMware)"]
        direction TB
        
        subgraph Cluster ["Clúster Hyper-V (Virtualización Anidada)"]
            direction LR
            subgraph HV01 ["HV01 · Nodo 1<br/>4 vCPU | 8-12 GB RAM | 80 GB"]
                WEB01["WEB01 (IIS)<br/>2 vCPU | 2 GB RAM | 40 GB"]
            end
            
            subgraph HV02 ["HV02 · Nodo 2<br/>4 vCPU | 8-12 GB RAM | 80 GB"]
                WEB02["WEB02 (IIS)<br/>2 vCPU | 2 GB RAM | 40 GB"]
            end
        end

        SAN01["SAN01 · Almacenamiento iSCSI<br/>2 vCPU | 4 GB RAM<br/>60 GB SO + 150 GB Datos"]
        MON01["MON01 · AD DS, DNS, Testigo y Monitor<br/>2 vCPU | 4-6 GB RAM | 80 GB"]

        Cluster <-->|iSCSI| SAN01
        Cluster <-->|Dominio / Quórum| MON01
    end

    style VMware fill:#f8f9fa,stroke:#adb5bd,stroke-width:2px
    style Cluster fill:#e9ecef,stroke:#495057,stroke-dasharray: 5 5
    style HV01 fill:#ffffff,stroke:#228be6,stroke-width:1.5px
    style HV02 fill:#ffffff,stroke:#228be6,stroke-width:1.5px
    style WEB01 fill:#e7f5ff,stroke:#339af0
    style WEB02 fill:#e7f5ff,stroke:#339af0
    style SAN01 fill:#fff4e6,stroke:#fd7e14
    style MON01 fill:#ebfbee,stroke:#40c057
