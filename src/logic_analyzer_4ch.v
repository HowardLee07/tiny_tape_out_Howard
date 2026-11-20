// SPDX-License-Identifier: Apache-2.0
`default_nettype none

module logic_analyzer_4ch (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       arm,
    input  wire [3:0] channels,
    input  wire [2:0] rd_addr,
    output wire [3:0] rd_data,
    output wire       done
);
    localparam [1:0] IDLE         = 2'b00,
                     WAIT_TRIGGER = 2'b01,
                     CAPTURE      = 2'b10,
                     READY        = 2'b11;

    reg [1:0] state;
    reg       prev_arm;
    reg       prev_ch0;
    reg [2:0] wr_addr;
    reg [3:0] samples [0:7];

    wire arm_rise = arm & ~prev_arm;
    wire trigger  = (state == WAIT_TRIGGER) & channels[0] & ~prev_ch0;

    always @(posedge clk) begin
        if (!rst_n) begin
            state    <= IDLE;
            prev_arm <= 1'b0;
            prev_ch0 <= 1'b0;
            wr_addr  <= 3'd0;
        end else begin
            prev_arm <= arm;
            prev_ch0 <= channels[0];

            // The trigger edge itself writes sample 0.
            if (trigger || state == CAPTURE)
                samples[wr_addr] <= channels;

            case (state)
                IDLE, READY: begin
                    if (arm_rise) begin
                        wr_addr <= 3'd0;
                        state   <= WAIT_TRIGGER;
                    end
                end

                WAIT_TRIGGER: begin
                    if (trigger) begin
                        wr_addr <= 3'd1;
                        state   <= CAPTURE;
                    end
                end

                CAPTURE: begin
                    if (wr_addr == 3'd7)
                        state <= READY;
                    else
                        wr_addr <= wr_addr + 3'd1;
                end

                default: state <= IDLE;
            endcase
        end
    end

    assign done    = (state == READY);
    assign rd_data = done ? samples[rd_addr] : 4'b0;
endmodule

`default_nettype wire
